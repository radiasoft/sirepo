from pykern.pkdebug import pkdp
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor


class CHX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self, scan_metadata):
        return [
            sirepo.raydata.scan_monitor.cfg.notebook_dir_chx.join(
                scan_metadata.get_start_field("cycle"),
                "AutoRuns",
                scan_metadata.get_start_field("user"),
                f"{scan_metadata.get_start_field('auto_pipeline')}.ipynb",
            )
        ]

    # def get_output_dir(self):
    #     raise NotImplementedError("# TODO(e-carlin): need to impl")
