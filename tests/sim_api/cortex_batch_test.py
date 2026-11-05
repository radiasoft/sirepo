"""test cortex batch api

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_all(fc):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo import auth_role
    from sirepo import srunit
    from sirepo.pkcli import roles

    def _batch(op_name, **op_args):
        return fc.sr_post(
            "cortexBatch",
            PKDict(op_name=op_name, op_args=PKDict(op_args)),
            raw_response=True,
        )

    fc.sr_post(
        "cortexDb",
        data=PKDict(op_name="insert_material", op_args=PKDict()),
        file_handle=pkunit.data_dir().join("input.xlsx").open("rb"),
    )
    # only admins manage the batch, guests get adm in dev
    with srunit.quest_start() as qcall:
        qcall.auth_db.model("UserRole").delete_roles(
            roles=[auth_role.ROLE_ADM], uid=fc.sr_uid
        )
    _batch("status").assert_http_status(403)
    roles.add(fc.sr_auth_state().uid, auth_role.ROLE_ADM)
    r = fc.sr_post("cortexBatch", PKDict(op_name="list_materials", op_args=PKDict()))
    pkunit.pkeq(1, len(r.rows))
    pkunit.pkeq(fc.sr_auth_state().uid, r.rows[0].uid)
    pkunit.pkeq(None, r.rows[0].completed)
    pkunit.pkeq(
        PKDict(is_running=False, jobs=[]),
        fc.sr_post("cortexBatch", PKDict(op_name="status", op_args=PKDict())),
    )
    # cortex.batch_uid is not configured
    pkunit.pkre(
        "not configured",
        str(
            fc.sr_post(
                "cortexBatch",
                PKDict(
                    op_name="run", op_args=PKDict(material_ids=[r.rows[0].material_id])
                ),
            )
        ),
    )
