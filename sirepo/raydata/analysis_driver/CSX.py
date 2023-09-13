from pykern import pkio
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor
import zipfile


class CSX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self, **kwargs):
        with zipfile.ZipFile(
            sirepo.raydata.scan_monitor.cfg.notebook_dir_csx.join(
                f"{self.catalog_name}.zip"
            ),
            "r",
        ) as z:
            z.extractall()
        return pkio.sorted_glob("*.ipynb")
