from pykern.pkdebug import pkdp
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor


class CHX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self, scan_metadata):
        pkdp("called get_notebooks for chx")
        notebook_path = (
            "/nsls2/data/chx/legacy/analysis/"
            + scan_metadata.get_scan_field("cycle")
            + "/AutoRuns/"
            + scan_metadata.get_scan_field("user")
            + "/"
            + scan_metadata.get_scan_field("auto_pipeline")
            + ".ipynb"
        )
        pkdp(f"notebook_path={notebook_path}")
        pass
