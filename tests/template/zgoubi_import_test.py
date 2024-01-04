"""PyTest for :mod:`sirepo.template.zgoubi_importer`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_importer(fc):
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
    from pykern.pkunit import pkeq, pkok
    from sirepo import sim_data, template
    import asyncio

    sim_type = "zgoubi"
    fc.sr_get_root(sim_type)
    for d in pkunit.case_dirs():
        res = fc.sr_post_form(
            "importFile",
            PKDict(folder="/importer_test"),
            PKDict(simulation_type=sim_type),
            file=d.join("in.dat"),
        )
        pkio.write_text(
            "parameters.py",
            fc.sr_get(
                "pythonSource",
                PKDict(
                    simulation_id=res.models.simulation.simulationId,
                    simulation_type=sim_type,
                ),
            ).data,
        )
