"""simulation data operations

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
import sirepo.srtime
import sirepo.util


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def prepare_import_file_args(cls, req):
        """Caches in lib dir"""

        def _path(ext):
            if ext != ".xlsx":
                raise sirepo.util.UserAlert(
                    f"invalid file extension='{ext}' must be 'xlsx'"
                )
            return cls.lib_file_name_with_type(
                sirepo.srtime.utc_now().strftime("%Y%m%d%H%M%S") + ext,
                "import-material",
            )

        rv = cls._prepare_import_file_name_args(req)
        p = _path(rv.ext_lower)
        cls.lib_file_write(p, req.form_file.as_bytes(), qcall=req.qcall)
        return rv.pkupdate(lib_file=p)

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)
