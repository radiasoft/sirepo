"""Analysis specific to CHX

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import sirepo.raydata.analysis_driver

_cfg = None


class CHX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_conda_env(self):
        return _cfg.conda_env

    def get_notebooks(self):
        return [
            PKDict(
                input_f=_cfg.input_base_dir.join(
                    self._scan_metadata.get_start_field("cycle"),
                    "AutoRuns",
                    self._scan_metadata.get_start_field("user"),
                    f"{self._scan_metadata.get_start_field('auto_pipeline')}.ipynb",
                ),
                output_f=_cfg.output_base_dir.join(
                    self._scan_metadata.get_start_field("cycle"),
                    self._scan_metadata.get_start_field("user"),
                    "ResPipelines",
                    f"{self._scan_metadata.get_start_field('auto_pipeline')}_{self.rduid}.ipynb",
                ),
            )
        ]

    def get_output_dir(self):
        return _cfg.output_base_dir.join(
            self._scan_metadata.get_start_field("cycle"),
            self._scan_metadata.get_start_field("user"),
            "Results",
            self.rduid,
        )

    def _get_papermill_args(self, *args, **kwargs):
        return [
            ["run_two_time", True],
            ["run_dose", False],
            ["username", self._scan_metadata.get_start_field("user")],
        ]


_cfg = pkconfig.init(
    input_base_dir=pkconfig.Required(
        pkio.py_path, "base directory for notebooks inputs"
    ),
    output_base_dir=pkconfig.Required(
        pkio.py_path, "base directory for notebooks and result outputs"
    ),
    conda_env=("analysis-2019-3.0.1-chx", str, "conda environment name"),
)
