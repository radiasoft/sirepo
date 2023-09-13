from pykern import pkio
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor
import zipfile


class CSX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self, **kwargs):
        with zipfile.ZipFile(self._notebook_zip_path(), "r") as z:
            z.extractall()
        return pkio.sorted_glob("*.ipynb")

    def _notebook_zip_path(self):
        # TODO(rorour) remove this function?
        return sirepo.raydata.scan_monitor.cfg.notebook_dir_csx.join(
            f"{self.catalog_name}.zip"
        )
