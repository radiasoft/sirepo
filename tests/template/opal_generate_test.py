# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.opal`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_generate_python():
    from pykern import pkio, pkunit
    from pykern.pkunit import pkeq
    from sirepo.template import opal

    with pkunit.save_chdir_work():
        for name in ("CSR Bend Drift", "CTF3 RF Photoinjector"):
            data = _example_data(name)
            data["report"] = "animation"
            actual = opal.python_source_for_model(data, model=None, qcall=None)
            outfile = name.lower().replace(" ", "-") + ".txt"
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            pkeq(expect, actual)


def _example_data(simulation_name):
    from sirepo import simulation_db
    from sirepo.template import opal

    for data in simulation_db.examples(opal.SIM_TYPE):
        if data.models.simulation.name == simulation_name:
            return simulation_db.fixup_old_data(data)[0]
    assert False
