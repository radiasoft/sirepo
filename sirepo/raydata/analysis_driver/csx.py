from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
import sirepo.raydata.analysis_driver
import sirepo.raydata.scan_monitor
import zipfile

_cfg = None


class CSX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_conda_env(self):
        return _cfg.conda_env

    def get_notebooks(self, **kwargs):
        with zipfile.ZipFile(
            _cfg.base_dir.join(f"{self.catalog_name}.zip"),
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
        return sirepo.raydata.scan_monitor.cfg.db_dir.join(self.rduid)


_cfg = pkconfig.init(
    base_dir=pkconfig.Required(
        pkio.py_path, "base directory for notebooks and outputs"
    ),
    conda_env=("2023-1.2-py39", str, "conda environment name"),
)
