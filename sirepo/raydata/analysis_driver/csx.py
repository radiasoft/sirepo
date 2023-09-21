from pykern import pkio
from pykern.pkcollections import PKDict
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor
import zipfile


class CSX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_notebooks(self, **kwargs):
        with zipfile.ZipFile(
            # TODO(e-carlin): this cfg should live in here
            sirepo.raydata.scan_monitor.cfg.notebook_dir_csx.join(
                f"{self.catalog_name}.zip"
            ),
            "r",
        ) as z:
            z.extractall()
        return [
            PKDict(
                input_f=p, output_f=p.dirpath().join(p.purebasename + "-out" + p.ext)
            )
            for p in pkio.sorted_glob("*.ipynb")
        ]

    def get_output_dir(self):
        return sirepo.raydata.scan_monitor.cfg.db_dir.join(self.uid)
