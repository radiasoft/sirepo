# -*- coding: utf-8 -*-
"""Import a single archive or json file

:copyright: Copyright (c) 2017-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import io
import pykern.pkio
import sirepo.sim_data
import sirepo.util
import zipfile


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
    ).req_data
    assert (
        not sim_type or d.simulationType == sim_type
    ), f"simulationType={d.simulationType} invalid, expecting={sim_type}"
    return d


async def read_zip(zip_bytes, qcall, sim_type=None):
    """Read zip file and store contents

    Args:
        zip_bytes (bytes): bytes to read
        sim_type (module): expected app

    Returns:
        PKDict: data
    """
    from sirepo import sim_data, sim_run

    with sim_run.tmp_dir(qcall=qcall) as tmp:
        data = None
        zipped = PKDict()
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
            for i in z.infolist():
                await sirepo.util.yield_to_event_loop()
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
        s = sim_data.get_class(data.simulationType)
        u = qcall.auth.logged_in_user()
        for n in s.lib_file_basenames(data):
            await sirepo.util.yield_to_event_loop()
            # TODO(robnagler) this does not allow overwrites of lib files,
            # but it needs to be modularized
            if s.lib_file_exists(n, qcall=qcall):
                continue
            # TODO(robnagler) raise useralert instead of an assert
            assert n in zipped, "auxiliary file={} missing in archive".format(n)
            needed.add(n)
        for b, src in zipped.items():
            await sirepo.util.yield_to_event_loop()
            if b in needed:
                src.copy(s.lib_file_write_path(b, qcall=qcall))
        return data
