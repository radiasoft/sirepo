"""Replay run uid(s).

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import asyncio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp
import copy
import databroker
import databroker.queries
import event_model
import time
import uuid


async def for_bluesky_plan(original_rduid, catalog_name, run_engine):
    await _replay_scan(str(uuid.uuid4()), original_rduid, catalog_name, run_engine)


async def _emit_new_document(
    destination_catalog_name,
    new_start_rduid,
    document_name,
    original_document,
    broker,
    run_engine,
):
    if document_name == "event_page":
        for e in event_model.unpack_event_page(original_document):
            await _emit_new_document(
                destination_catalog_name,
                new_start_rduid,
                "event",
                e,
                broker,
                run_engine,
            )
    elif document_name == "datum_page":
        for d in event_model.unpack_datum_page(original_document):
            await _emit_new_document(
                destination_catalog_name,
                new_start_rduid,
                "datum",
                d,
                broker,
                run_engine,
            )
    else:
        await run_engine.emit(
            # TODO(e-carlin): doc
            event_model.DocumentNames[document_name],
            _get_new_document(document_name, original_document, new_start_rduid),
        )
        # run_engine.emit doesn't actually yield. So, need to fake our
        # own cooperation.
        # https://github.com/bluesky/bluesky/blob/4bd5bc6c420a61ef7c2c76561aab44dc1bf22c37/bluesky/run_engine.py#L2571
        await asyncio.sleep(0)


def _get_new_document(document_name, original_document, new_start_rduid):
    if type(original_document) == dict:
        n = copy.deepcopy(original_document)
    else:
        n = original_document.to_dict()

    if document_name not in {"datum"}:
        n["uid"] = new_start_rduid if document_name == "start" else str(uuid.uuid4())
    if document_name not in {"datum", "resource"}:
        n["time"] = time.time()
    if "run_start" in n:
        n["run_start"] = new_start_rduid
    if "datum_id" in n:
        n["datum_id"] = str(uuid.uuid4())
    return n


# TODO(e-carlin): convert to class (don't have to pass broker, run engine, etc around)
async def _replay_scan(new_start_rduid, old_start_rduid, catalog_name, run_engine):
    p = None
    b = databroker.catalog[catalog_name]
    # fill="no" to conserve space
    for n, d in b[old_start_rduid].documents(fill="no"):
        t = d.get("time")
        if isinstance(t, list):
            if len(t) > 1:
                assert (
                    n == "event_page"
                ), f"uid={old_start_rduid} document={n} has times={t}, a list longer than one is only allowed for event_page"
            t = t[0]
        if not t:
            await _emit_new_document(catalog_name, new_start_rduid, n, d, b, run_engine)
            continue
        if n == "start":
            assert t and not p, f"expecting t={t} and not p={p}"
            p = t
        if t:
            s = t - p
            if s > 0:
                # Approximates spacing between document emits in real
                # life.
                # Doesn't take into account things like the time it
                # takes to emit the doc. The approximation should be good
                # enough because the times not taken into account are
                # small.
                await asyncio.sleep(s)
            p = t
        await _emit_new_document(catalog_name, new_start_rduid, n, d, b, run_engine)
