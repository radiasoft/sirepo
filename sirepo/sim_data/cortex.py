"""simulation data operations

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import re
import sirepo.sim_data
import sirepo.srtime
import sirepo.util


class SimData(sirepo.sim_data.SimDataBase):
    SUMMARY_GLOB = "*-summary.json"

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)

    @classmethod
    def parts_from_summary_file(cls, filename):
        m = re.search(r"(.*?)-(.*?)-summary.json", filename)
        if not m:
            raise AssertionError(f"Unexpected summary filename: {filename}")
        return m.group(1, 2)

    @classmethod
    def summary_file_from_parts(cls, report, material_id):
        return f"{report}-{material_id}-summary.json"

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "tileAnimation" in analysis_model:
            return "tileAnimation"
        if "slabAnimation" in analysis_model:
            return "slabAnimation"
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
