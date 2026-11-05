"""test the batch user's sim for a material

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_batch_user_sim():
    from pykern import pkunit
    from sirepo import srunit
    import asyncio
    import sirepo.sim_api.cortex
    import sirepo.sim_api.cortex.batch

    async def _op(batch):
        with batch._qcall() as q:
            s = await sirepo.sim_api.cortex.get_sim_data(q, 123)
            pkunit.pkeq(None, s)
            s = await sirepo.sim_api.cortex.get_sim_data(q, 123, create=True)
            pkunit.pkeq("123", s.models.simulation.name)
            pkunit.pkeq(
                s.models.simulation.simulationId,
                (
                    await sirepo.sim_api.cortex.get_sim_data(q, 123)
                ).models.simulation.simulationId,
            )
            return q.auth.logged_in_user()

    with srunit.quest_start(want_user=True) as qcall:
        u = qcall.auth.logged_in_user()
    pkunit.pkeq(u, asyncio.run(_op(sirepo.sim_api.cortex.batch._Batch(u, []))))
