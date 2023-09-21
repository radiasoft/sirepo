from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor


class CHX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self):
        return [
            PKDict(
                # TODO(e-carlin): this cfg should live in here
                input_f=sirepo.raydata.scan_monitor.cfg.notebook_dir_chx.join(
                    self._scan_metadata.get_start_field("cycle"),
                    "AutoRuns",
                    self._scan_metadata.get_start_field("user"),
                    f"{self._scan_metadata.get_start_field('auto_pipeline')}.ipynb",
                ),
                output_f=sirepo.raydata.scan_monitor.cfg.notebook_dir_chx.join(
                    self._scan_metadata.get_start_field("cycle"),
                    self._scan_metadata.get_start_field("user"),
                    "ResPipelines"
                    f"{self._scan_metadata.get_start_field('auto_pipeline')}_{self.uid}.ipynb",
                ),
            )
        ]

    def _get_papermill_args(self, *args, **kwargs):
        return [
            ["run_two_time", True],
            ["run_dose", False],
            ["username", self._scan_metadata.get_start_field("user")],
        ]

    def get_output_dir(self):
        return sirepo.raydata.scan_monitor.cfg.notebook_dir_chx.join(
            self._scan_metadata.get_start_field("cycle"),
            self._scan_metadata.get_start_field("user"),
            "Results",
            self.uid,
        )
