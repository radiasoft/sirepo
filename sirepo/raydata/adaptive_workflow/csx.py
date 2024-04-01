"""CSX specific adaptive workflow operations.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkdebug import pkdlog, pkdp
import sirepo.raydata.adaptive_workflow

_cfg = None


class CSX(sirepo.raydata.adaptive_workflow.Base):
    async def run_engine_event_callback_fccd_stats1_total(self, document_data):
        if not (f := document_data.get("fccd_stats1_total")):
            pkdlog("expecting fccd_stats1_total in document_data={}", document_data)
            return
        if f < _cfg.fccd_stats1_total_threshold:
            return
        pkdlog(
            "fccd_stats1_total={} > fccd_stats1_total_threshold={} stopping current plan",
            f,
            _cfg.fccd_stats1_total_threshold,
        )
        await self._qserver_client.stop_current_plan()


_cfg = pkconfig.init(
    fccd_stats1_total_threshold=(
        123385.0,
        float,
        "Threshold to trigger progression of adaptive workflow",
    ),
)
