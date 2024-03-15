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

    def post(self):
        d = PKDict(pkjson.load_any(self.request.body))
        u = self._rs_authenticate(d.simulationType)
        return self.write(
            sirepo.global_resources.for_simulation(
                d.simulationType,
                d.simulationId,
                uid=u,
                for_gui=False,
            )
        )

    def _rs_authenticate(self, sim_type):
        assert (
            sirepo.feature_config.cfg().enable_global_resources
        ), "global resources supervisor api called but system not enabled"
        u = super()._rs_authenticate()
        with sirepo.quest.start() as qcall:
            with qcall.auth.logged_in_user_set(u):
                try:
                    qcall.auth.check_sim_type_role(
                        sim_type, force_sim_type_required_for_api=True
                    )
                except Exception as e:
                    pkdlog(
                        "user={} does not have access to sim_type={} error={} stack={}",
                        u,
                        sim_type,
                        e,
                        pkdexc(),
                    )
                    raise sirepo.tornado.error_forbidden()
        return u
