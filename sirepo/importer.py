# -*- coding: utf-8 -*-
"""Import a single archive

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from pykern import pkcompat
import base64
import pykern.pkio
import sirepo.util
import six
import zipfile
import os


def do_form(form, qcall):
    """Self-extracting archive post

    Args:
        form (flask.request.Form): what to import

    Returns:
        dict: data
    """
    from sirepo import simulation_db

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
        dict: data
    """
    from sirepo import simulation_db

    # attempt to decode the input as json first, if valid try python
    # fixup data in case new structures are need for lib_file ops below
    # need to verify_app_directory here, because this may be the
    # first point we know sim_type.
    data = simulation_db.json_load(text)
    data = simulation_db.fixup_old_data(data, qcall=qcall)[0]
    assert (
        not sim_type or data.simulationType == sim_type
    ), "simulationType={} invalid, expecting={}".format(
        data.simulationType,
        sim_type,
    )
    return qcall.parse_post(req_data=data).req_data


def read_zip(zip_bytes, qcall, sim_type=None):
    """Read zip file and store contents

    Args:
        zip_bytes (bytes): bytes to read
        sim_type (module): expected app

    Returns:
        dict: data
    """
    from sirepo import simulation_db, sim_data, sim_run

    with sim_run.tmp_dir(qcall=qcall) as tmp:
        pkdp("\n\n\ntmp={}", tmp)
        data = None
        zipped = PKDict()
        with zipfile.ZipFile(six.BytesIO(zip_bytes), "r") as z:
            for i in z.infolist():
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

        with zipfile.ZipFile(six.BytesIO(zip_bytes), "r") as z:
            pkdp("\n\n\n z.infolist()={}", z.infolist())
            for i in z.infolist():
                b = pykern.pkio.py_path(i.filename).basename
                pkdp("\n\n\nb={}", b)
                c = z.read(i)
                if "related_sim" in b:
                    index = int(b.split(".")[0][-1])
                    d = simulation_db.json_load(c)
                    pkdp("\n\n\n d={}, d.type={}", d, type(d))
                    pkdp("\n\n\n idx ={}", b.split(".")[0][-1])
                    d.models.simulation.isExample = False
                    d.models.simulation.folder = "/Omega"
                    s = simulation_db.save_new_simulation(
                        d,
                        qcall=qcall,
                    )
                    # TODO: get lib files
                    # for lib_file in relsim_lib_files(related_sim):
                        # copy_to_sim_type_lib_dir(lib_file)
                    data.models.simWorkflow.coupledSims[
                        index
                    ].simulationId = s.models.simulation.simulationId

        needed = set()
        s = sim_data.get_class(data.simulationType)
        u = qcall.auth.logged_in_user()
        for n in s.lib_file_basenames(data):
            # TODO(robnagler) this does not allow overwrites of lib files,
            # but it needs to be modularized
            if s.lib_file_exists(n, qcall=qcall):
                continue
            # TODO(robnagler) raise useralert instead of an assert
            assert n in zipped, "auxiliary file={} missing in archive".format(n)
            needed.add(n)
        for b, src in zipped.items():
            if b in needed:
                src.copy(s.lib_file_write_path(b, qcall=qcall))
        pkdp("\n\n\nls tmp={}", os.listdir(tmp))
        # TODO: get the related sims saved to their respective sim dirs? or
        # something along those lines? copy_related_sim needs to be able to
        # find.
        return data
