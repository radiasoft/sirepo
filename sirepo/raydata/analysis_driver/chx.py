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
    def get_notebooks(self):
        return [
            PKDict(
                input_f=_cfg.base_dir.join(
                    self._scan_metadata.get_start_field("cycle"),
                    "AutoRuns",
                    self._scan_metadata.get_start_field("user"),
                    f"{self._scan_metadata.get_start_field('auto_pipeline')}.ipynb",
                ),
                output_f=_cfg.base_dir.join(
                    self._scan_metadata.get_start_field("cycle"),
                    self._scan_metadata.get_start_field("user"),
                    "RResPipelines",
                    f"{self._scan_metadata.get_start_field('auto_pipeline')}_{self.uid}.ipynb",
                ),
            )
        ]

    def get_output_dir(self):
        return _cfg.base_dir.join(
            self._scan_metadata.get_start_field("cycle"),
            self._scan_metadata.get_start_field("user"),
            "RResults",
            self.uid,
        )

    def _get_papermill_args(self, *args, **kwargs):
        return [
            ["run_two_time", True],
            ["run_dose", False],
            ["username", self._scan_metadata.get_start_field("user")],
        ]


_cfg = pkconfig.init(
    base_dir=pkconfig.Required(
        pkio.py_path, "base directory for notebooks and outputs"
    ),
)
