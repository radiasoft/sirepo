# -*- coding: utf-8 -*-
"""exporter test

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_create_zip(fc):
    from pykern import pkio
    from pykern import pkunit
    from pykern import pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern.pkunit import pkeq
    from sirepo import srunit
    import base64
    import re
    import zipfile

    imported = _import(fc)
    for sim_type, sim_name, expect in imported + [
        (
            "elegant",
            "bunchComp - fourDipoleCSR",
            ["WAKE-inputfile.knsl45.liwake.sdds", "run.py", "sirepo-data.json"],
        ),
        (
            "srw",
            "Tabulated Undulator Example",
            ["anything/magnetic_measurements.zip", "run.py", "sirepo-data.json"],
        ),
        ("warppba", "Laser Pulse", ["run.py", "sirepo-data.json"]),
        (
            "opal",
            "CSR Bend Drift",
            ["opal.in", "sirepo-data.json"],
        ),
        (
            "genesis",
            "PEGASUS FEL",
            ["genesis.in", "sirepo-data.json"],
        ),
        (
            "madx",
            "FODO PTC",
            ["madx.madx", "sirepo-data.json"],
        ),
    ]:
        sim_id = fc.sr_sim_data(sim_name, sim_type)["models"]["simulation"][
            "simulationId"
        ]
        with pkio.save_chdir(pkunit.work_dir()) as d:
            r = fc.sr_get(
                "exportArchive",
                PKDict(
                    simulation_type=sim_type,
                    simulation_id=sim_id,
                    filename="anything.zip",
                ),
            )
            p = d.join(sim_name + ".zip")
            x = r.data
            p.write_binary(x)
            pkeq(
                expect,
                sorted(zipfile.ZipFile(str(p)).namelist()),
            )


def _import(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern import pkio
    from pykern import pkunit
    import zipfile

    res = []
    for f in pkio.sorted_glob(pkunit.data_dir().join("*.zip")):
        with zipfile.ZipFile(str(f)) as z:
            expect = sorted([x for x in z.namelist() if not x[-1] == "/"] + ["run.py"])
        d = fc.sr_post_form(
            "importFile",
            PKDict(folder="/exporter_test"),
            PKDict(simulation_type=f.basename.split("_")[0]),
            file=f,
        )
        res.append((d.simulationType, d.models.simulation.name, expect))
    return res
