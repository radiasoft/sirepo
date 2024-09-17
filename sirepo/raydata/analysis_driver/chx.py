"""Analysis specific to CHX

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import os.path
import sirepo.raydata.analysis_driver

_cfg = None


class CHX(sirepo.raydata.analysis_driver.AnalysisDriverBase):
    def get_conda_env(self):
        return _cfg.conda_env

    def get_detailed_status_file(self, rduid, *args, **kwargs):
        p = self.get_output_dir().join(f"progress_dict_{rduid}.json")
        if not p.check():
            return None
        d = pkjson.load_any(p)
        # The notebooks do json.dump(json.dumps(progress_dict), outfile)
        # which double encodes the json object. So, we may
        # need to decode it 2x. Be compliant either way in case this
        # changes in the future.
        return pkjson.load_any(d) if isinstance(d, str) else d

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

    def is_scan_elegible_for_analysis(self):
        return bool(self._scan_metadata.get_start_field("cycle", unchecked=True))

    def _get_papermill_args(self, *args, **kwargs):
        return [
            # Cycle can look like 2024_2 which is converted to int by papermill unless raw_param=True
            PKDict(
                name="cycle",
                value=self._scan_metadata.get_start_field("cycle"),
                raw_param=True,
            ),
            # POSIT: Same as AutoRun_functions.get_process_id
            PKDict(name="process_id", value=f"{self.rduid}_0"),
            PKDict(name="username", value=self._scan_metadata.get_start_field("user")),
            PKDict(
                name="user_group",
                value=self._scan_metadata.get_start_field("user_group", unchecked=True),
            ),
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
