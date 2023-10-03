# -*- coding: utf-8 -*-
"""Import a single archive or json file

:copyright: Copyright (c) 2017-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import base64
import pykern.pkio
import sirepo.sim_data
import sirepo.util
import six
import zipfile


def do_form(form, qcall):
    """Self-extracting archive post

    Args:
        form (flask.request.Form): what to import

    Returns:
        dict: data
    """

    if not "zip" in form:
        raise sirepo.util.NotFound("missing zip in form")
    data = read_zip(base64.decodebytes(pkcompat.to_bytes(form["zip"])), qcall)
    data.models.simulation.folder = "/Import"
    data.models.simulation.isExample = False
    return simulation_db.save_new_simulation(data, qcall=qcall)


def read_json(text, qcall, sim_type=None):
    """Read json file and return

    Args:
        text (IO): file to be read
        sim_type (str): expected type

    Returns:
        PKDict: data
    """

    # attempt to decode the input as json, then parse it like it is an incoming
    d = qcall.parse_post(
        req_data=simulation_db.fixup_old_data(
            data=simulation_db.json_load(text),
            qcall=qcall,
        )[0],
        # this data should not go through react_unformat_data, because
        # it has come from a disk via exportArchive, and not gone through
        # reacts data management.
        is_sim_data=False,
    ).req_data
    assert (
        not sim_type or d.simulationType == sim_type
    ), f"simulationType={d.simulationType} invalid, expecting={sim_type}"
    return d


def read_zip(zip_bytes, qcall, sim_type=None):
    """Read zip file and store contents

    Args:
        zip_bytes (bytes): bytes to read
        sim_type (module): expected app

    Returns:
        PKDict: data
    """
    with simulation_db.tmp_dir(qcall=qcall) as tmp:
        data = None
        zipped = PKDict()
        with zipfile.ZipFile(six.BytesIO(zip_bytes), "r") as z:
            for i in z.infolist():
                sirepo.util.yield_to_event_loop()
                b = pykern.pkio.py_path(i.filename).basename
                c = z.read(i)
                if b.lower() == simulation_db.SIMULATION_DATA_FILE:
                    assert not data, "too many db files {} in archive".format(b)
                    data = read_json(c, qcall, sim_type)
                    continue
                if "__MACOSX" in i.filename:
                    continue
                # TODO(robnagler) ignore identical files hash
                assert not b in zipped, "{} duplicate file in archive".format(
                    i.filename
                )
                zipped[b] = tmp.join(b)
                zipped[b].write(c, "wb")
        assert data, "missing {} in archive".format(simulation_db.SIMULATION_DATA_FILE)
        needed = set()
        s = sirepo.sim_data.get_class(data.simulationType)
        u = qcall.auth.logged_in_user()
        for n in s.lib_file_basenames(data):
            sirepo.util.yield_to_event_loop()
            # TODO(robnagler) this does not allow overwrites of lib files,
            # but it needs to be modularized
            if s.lib_file_exists(n, qcall=qcall):
                continue
            # TODO(robnagler) raise useralert instead of an assert
            assert n in zipped, "auxiliary file={} missing in archive".format(n)
            needed.add(n)
        for b, src in zipped.items():
            sirepo.util.yield_to_event_loop()
            if b in needed:
                src.copy(s.lib_file_write_path(b, qcall=qcall))
        return data
