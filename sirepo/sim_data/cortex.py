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
    #: json of the sim summary inside the summary zip
    SUMMARY_JSON = "summary.json"

    SUMMARY_GLOB = "*-summary.zip"

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)

    @classmethod
    def parts_from_summary_file(cls, filename):
        m = re.search(r"^(.*?)-(\d+)-summary\.zip$", filename)
        if not m:
            raise AssertionError(f"Unexpected summary filename: {filename}")
        return m.group(1), int(m.group(2))

    @classmethod
    def summary_file_from_parts(cls, report, material_id):
        """Zip of the summary json, and the png and hdf5 files of a sim"""
        return f"{report}-{material_id}-summary.zip"

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
