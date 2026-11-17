"""test the cortexSim pathway_analysis op

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest

pytest.importorskip("openmc_pathway_analysis")

_MODEL = "hcpbSlabAnimation"


def test_pathway_analysis_op(fc):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo.sim_api.cortex import material_db
    import cortex_pathway_test
    import datetime
    import sirepo.sim_data

    s = sirepo.sim_data.get_class("cortex")

    def _analyze(material_id, op_name="pathway_analysis", **kwargs):
        return fc.sr_post(
            "cortexSim",
            PKDict(
                op_name=op_name,
                op_args=PKDict(
                    material_id=material_id,
                    is_public=False,
                    model=_MODEL,
                    metric="activity",
                    by_element=False,
                    cooling_seconds=100 * 365 * 24 * 3600,
                ).pkupdate(kwargs),
            ),
        )

    def _staged(name):
        return fc.sr_user_dir().join("cortex", "lib", name)

    m = fc.sr_post(
        "cortexDb",
        data=PKDict(op_name="insert_material", op_args=PKDict()),
        file_handle=pkunit.data_dir().join("input.xlsx").open("rb"),
    ).op_result.material_id
    pkunit.pkre("not available", _analyze(m).error)
    cortex_pathway_test.write_inputs(material_db.cortexdb_path(m, _MODEL))
    r = _analyze(m)
    # not plasma facing
    pkunit.pkeq("First_Wall", r.layer)
    pkunit.pkeq(["I135"], [x.name for x in r.rows])
    p = _staged(s.pathway_lib_file("results"))
    t = p.mtime()
    pkunit.pkeq(["I"], [x.name for x in _analyze(m, by_element=True).rows])
    pkunit.pkeq(t, p.mtime(), "staged again for the same run")
    # production pathway of a final nuclide, same inputs
    pkunit.pkeq(
        "Xe135",
        _analyze(m, op_name="pathway_nuclide", nuclide="Xe135").chain[-1].name,
    )
    pkunit.pkeq(t, p.mtime(), "staged again for the pathway of a nuclide")
    with pkunit.pkexcept("httpException"):
        _analyze(m, model="../x")
    # another user can analyze it once it's public
    u = fc.sr_uid
    material_db.update_sim_summary(
        PKDict(
            material_id=m,
            model=_MODEL,
            version="1",
            completed=datetime.datetime.now(datetime.timezone.utc),
            values=[],
            plots=[],
        ),
        u,
    )
    fc.sr_logout()
    fc.sr_login_as_guest()
    pkunit.pkne(u, fc.sr_uid)
    with pkunit.pkexcept("httpException"):
        _analyze(m)
    with pkunit.pkexcept("httpException"):
        _analyze(m, is_public=True)
    material_db.set_public(m, True, u)
    pkunit.pkeq(["I135"], [x.name for x in _analyze(m, is_public=True).rows])
    pkunit.pkok(_staged(s.PATHWAY_STAMP).exists(), "not staged in the other user's lib")
