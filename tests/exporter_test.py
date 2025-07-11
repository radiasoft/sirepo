"""exporter test

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import contextlib


def test_create_zip(fc):
    from pykern import pkunit
    from pykern import pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern.pkunit import pkeq, pkok
    from sirepo import srunit
    import base64
    import re
    import zipfile

    @contextlib.contextmanager
    def _out_dir():
        from pykern import pkio, pkunit

        with pkio.save_chdir(pkunit.work_dir()) as rv:
            d = fc.sr_db_dir()
            p = d.stat().mode & 0o777
            try:
                d.chmod(0o500)
                yield rv
            finally:
                d.chmod(p)

    with _out_dir() as out_dir:
        imported = _import(fc)
        for sim_type, sim_name, expect, data_value in imported + [
            (
                "elegant",
                "bunchComp - fourDipoleCSR",
                ["WAKE-inputfile.knsl45.liwake.sdds", "run.py", "sirepo-data.json"],
                "",
            ),
            (
                "srw",
                "Tabulated Undulator Example",
                ["anything/magnetic_measurements.zip", "run.py", "sirepo-data.json"],
                '"verticalRange": "15"',
            ),
            ("warppba", "Laser Pulse", ["run.py", "sirepo-data.json"], ""),
            (
                "opal",
                "CSR Bend Drift",
                ["opal.in", "sirepo-data.json"],
                "",
            ),
            (
                "genesis",
                "PEGASUS FEL",
                ["genesis.in", "sirepo-data.json"],
                "",
            ),
            (
                "madx",
                "FODO PTC",
                ["madx.madx", "sirepo-data.json"],
                "",
            ),
        ]:
            sim_id = fc.sr_sim_data(sim_name, sim_type).models.simulation.simulationId
            r = fc.sr_get(
                "exportArchive",
                PKDict(
                    simulation_type=sim_type,
                    simulation_id=sim_id,
                    filename="anything.zip",
                ),
            )
            r.assert_success()
            p = out_dir.join(sim_name + ".zip")
            p.write_binary(r.data)
            pkeq(
                expect,
                sorted(zipfile.ZipFile(str(p)).namelist()),
            )
            if data_value:
                d = pkcompat.from_bytes(
                    zipfile.ZipFile(str(p)).read("sirepo-data.json")
                )
                pkok(re.search(data_value, d), "")


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
        res.append((d.simulationType, d.models.simulation.name, expect, ""))
    return res
