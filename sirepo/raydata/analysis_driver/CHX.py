from pykern.pkdebug import pkdp
import pykern.pkio
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor


class CHX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self, scan_metadata):
        return [
            sirepo.raydata.scan_monitor.cfg.notebook_dir_chx.join(
                scan_metadata.get_scan_field("cycle"),
                "AutoRuns",
                scan_metadata.get_scan_field("user"),
                f"{scan_metadata.get_scan_field('auto_pipeline')}.ipynb",
            )
        ]
