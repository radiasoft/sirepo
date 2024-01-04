"""PyTest for :mod:`sirepo.template.zgoubi_importer`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_importer(fc):
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
    import re

    for d in pkunit.case_dirs(group_prefix="rad"):
        m = re.search("^(.+?)-", d.basename)
        sim_type = m.group(1)
        fc.sr_get_root(sim_type)
        res = fc.sr_post_form(
            "importFile",
            PKDict(folder="/importer_test"),
            PKDict(simulation_type=sim_type),
            # NOTE: first file must be first
            file=pkio.sorted_glob("*")[0],
        )
        pkunit.pkok("models" in res, "no models in res={}", res)
        pkio.write_text(
            "pythonSource.txt",
            fc.sr_get(
                "pythonSource",
                PKDict(
                    simulation_id=res.models.simulation.simulationId,
                    simulation_type=sim_type,
                ),
            ).data,
        )
