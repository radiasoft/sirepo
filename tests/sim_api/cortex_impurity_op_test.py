"""test the cortexSim impurity_comparison op

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_MODEL = "hcpbSlabAnimation"


def test_impurity_comparison_op(fc):
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    from sirepo.sim_api.cortex import material_db
    import cortex_impurity_test
    import sirepo.template.cortex

    def _compare(material_id, **kwargs):
        return fc.sr_post(
            "cortexSim",
            PKDict(
                op_name="impurity_comparison",
                op_args=PKDict(
                    material_id=material_id,
                    is_public=False,
                    model=_MODEL,
                ).pkupdate(kwargs),
            ),
        )

    m = fc.sr_post(
        "cortexDb",
        data=PKDict(op_name="insert_material", op_args=PKDict()),
        file_handle=pkunit.data_dir().join("input.xlsx").open("rb"),
    ).op_result.material_id
    pkunit.pkre("Run the impurity simulations", _compare(m).error)
    # not plasma facing, so the First Wall
    x = cortex_impurity_test.impurity_inputs("First_Wall")
    for i in ("max", "min"):
        d = pkio.mkdir_parent(
            material_db.cortexdb_path(
                m, sirepo.template.cortex.impurity_report(_MODEL, i)
            )
        )
        f = sirepo.template.cortex.impurity_comparison_files("First_Wall")
        for k, v in x[i].items():
            pkio.write_text(d.join(f[k]), v)
    r = _compare(m)
    pkunit.pkeq("First Wall", r.layer)
    pkunit.pkeq(
        ["waste", "waste_struct_scaled", "shutdown_dose", "decay_heat"],
        [x.name for x in r.plots],
    )
    pkunit.pkeq(
        PKDict(max="Class B", min="Class A"),
        PKDict(
            max=r.classes.waste[0].max.nrcClass,
            min=r.classes.waste[0].min.nrcClass,
        ),
    )
    pkunit.pkeq(b"\x89PNG", bytes(r.plots[2].png[:4]))
    # an impurity report isn't a neutronics report
    with pkunit.pkexcept("httpException"):
        _compare(m, model="hcpbSlabMinImpurityAnimation")
    # another user's material
    fc.sr_logout()
    fc.sr_login_as_guest()
    with pkunit.pkexcept("httpException"):
        _compare(m)
