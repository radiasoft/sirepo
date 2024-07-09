"""Supervisor API to get global resources for a simulation.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import sirepo.agent_supervisor_api
import sirepo.feature_config
import sirepo.global_resources
import sirepo.tornado


class Req(sirepo.agent_supervisor_api.ReqBase):
    _TOKEN_TO_UID = PKDict()
    _UID_TO_TOKEN = PKDict()

    def _sr_authenticate(self, token, *args, **kwargs):
        assert (
            sirepo.feature_config.cfg().enable_global_resources
        ), "global resources supervisor api called but system not enabled"
        u = super()._sr_authenticate(token)
        with sirepo.quest.start() as qcall:
            with qcall.auth.logged_in_user_set(u):
                s = None
                try:
                    s = pkjson.load_any(self.request.body).simulationType
                    qcall.auth.check_sim_type_role(
                        s, force_sim_type_required_for_api=True
                    )
                except Exception as e:
                    pkdlog(
                        "user={} does not have access to sim_type={} error={} stack={}",
                        u,
                        s,
                        e,
                        pkdexc(),
                    )
                    raise sirepo.tornado.error_forbidden()
        return u

    async def _sr_post(self, uid, *args, **kwargs):
        d = PKDict(pkjson.load_any(self.request.body))
        return self.write(
            sirepo.global_resources.for_simulation(
                d.simulationType,
                d.simulationId,
                uid=uid,
                for_gui=False,
            )
        )
