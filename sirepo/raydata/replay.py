from pykern.pkcollections import PKDict
import copy
import databroker
import databroker.queries
import event_model
import random
import time
import uuid


def begin(source_catalog, destination_catalog, num_scans):
    def _emit_new_document(
        destination_catalog_name,
        new_rduid,
        document_name,
        original_document,
        broker,
    ):
        if document_name == "event_page":
            for e in event_model.unpack_event_page(original_document):
                _emit_new_document(
                    destination_catalog_name, new_rduid, "event", e, broker
                )
        elif document_name == "datum_page":
            for d in event_model.unpack_datum_page(original_document):
                _emit_new_document(
                    destination_catalog_name, new_rduid, "datum", d, broker
                )
        else:
            f = PKDict(rduid=new_rduid)
            if document_name not in {"datum", "resource"}:
                f.pkupdate(time=time.time())
            broker.insert(
                document_name,
                _get_new_document(document_name, original_document, f),
            )

    def _get_new_document(document_name, original_document, updated_fields):
        if type(original_document) == dict:
            n = copy.deepcopy(original_document)
        else:
            n = original_document.to_dict()

        for k in updated_fields.keys():
            if k != "rduid":
                n[k] = updated_fields[k]

        if document_name == "start":
            n["rduid"] = updated_fields["rduid"]
        elif "run_start" in n:
            n["run_start"] = updated_fields["rduid"]
        return n

    def _replay_scan(
        new_rduid, old_rduid, source_catalog_name, destination_catalog_name
    ):
        # Need to use the same broker for all documents associated with same scan
        b = databroker.catalog[destination_catalog_name].v1
        # fill="no" to conserve space (using "yes" OOM Killer tends to kill the process)
        for n, d in databroker.catalog[source_catalog_name][old_rduid].documents(
            fill="no"
        ):
            _emit_new_document(destination_catalog_name, new_rduid, n, d, b)

    def _replay_scans(source_catalog_name, destination_catalog_name, num_scans):
        for n, o in {
            str(uuid.uuid4()): u
            for u in random.choices(
                list(databroker.catalog[source_catalog_name]), k=num_scans
            )
        }.items():
            _replay_scan(n, o, source_catalog_name, destination_catalog_name)

    _replay_scans(source_catalog, destination_catalog, int(num_scans))
