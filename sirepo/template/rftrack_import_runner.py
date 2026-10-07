"""Run a self-contained RF-Track script under import, in isolation.

Stage 2 (parent side) of importing an arbitrary RF-Track Python script
into a Sirepo rftrack simulation (see rftrack-import-plan.md). `run()`
hands the script to `rftrack_import_driver` in a fresh subprocess, with a
timeout, so a hand-written script's crash or heavy resource use can't
affect the Sirepo process driving the import; `rftrack_import_driver`
installs `rftrack_import_recorder` there and runs the script against it.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import pykern.pkio
import pykern.pkjson
import subprocess
import sys
import tempfile

#: written into the scratch dir the driver subprocess runs in
_RESULT_BASENAME = "rftrack_import_result.json"
_SCRIPT_BASENAME = "rftrack_import_script.py"

_cfg = pykern.pkconfig.init(
    timeout_secs=(
        30,
        pykern.pkconfig.parse_seconds,
        "how long a script under import may run before being killed",
    ),
)


def run(script_text, data_files=None):
    """Execute `script_text` under the RF_Track call recorder.

    Args:
        script_text (str): the uploaded script's contents
        data_files (dict): basename -> content, written alongside the
            script in its scratch directory before running it -- for a
            test to exercise the "the referenced field-map file actually
            exists" path (see `rftrack_import_driver.py`'s
            `_stub_missing_data_files()` for the "doesn't exist" path,
            which needs no files here at all) [None]

    Returns:
        PKDict: the driver's "ok" result -- `calls` (one resolved
            PKDict(kind, args, kwargs, accessors) per recorded RF_Track
            call, in call order) and `number_of_threads`

    Raises:
        IOError: the script timed out, could not run (e.g. a missing
            dependency), or raised while running
    """
    with tempfile.TemporaryDirectory(prefix="rftrack-import-") as d:
        d = pykern.pkio.py_path(d)
        s = d.join(_SCRIPT_BASENAME)
        r = d.join(_RESULT_BASENAME)
        pykern.pkio.write_text(s, script_text)
        for n, c in (data_files or {}).items():
            pykern.pkio.write_text(d.join(n), c)
        try:
            p = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "sirepo.template.rftrack_import_driver",
                    str(s),
                    str(r),
                ],
                cwd=str(d),
                capture_output=True,
                text=True,
                timeout=_cfg.timeout_secs,
            )
        except subprocess.TimeoutExpired:
            raise IOError(f"script exceeded {_cfg.timeout_secs}s timeout")
        if not r.exists():
            raise IOError(
                f"script import produced no result, exit={p.returncode}"
                + f" stderr={p.stderr}"
            )
        res = pykern.pkjson.load_any(r)
        if res.status != "ok":
            raise IOError(_error_message(res))
        return res


def _error_message(res):
    if res.reason == "missing_dependencies":
        return "script requires packages not available: " + ", ".join(res.missing)
    if res.reason == "script_exception":
        return f"script raised: {res.message}"
    return f"script import failed: {res}"
