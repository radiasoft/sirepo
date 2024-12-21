"""setup development directory

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkconfig
from pykern import pkio
import pathlib
import sirepo.const


def default_command():
    global cfg

    assert pkconfig.in_dev_mode(), "Only to be used in dev. channel={}".format(
        pkconfig.cfg.channel
    )
    cfg = pkconfig.init(
        proprietary_code_uri=(
            f"file://{pkio.py_path(sirepo.const.DEV_SRC_RADIASOFT_DIR).join('rsconf/proprietary')}",
            str,
            "root uri of proprietary codes files location",
        ),
    )
    _proprietary_codes()


def _proprietary_codes():
    """Get proprietary files and put it in the proprietary code dir

    Args:
      uri (str): where to get file (file:// or http://)
    """
    import sirepo.feature_config
    import sirepo.sim_data
    import sirepo.srdb
    import subprocess
    import urllib.error
    import urllib.request

    for s in sirepo.feature_config.proprietary_sim_types():
        f = sirepo.sim_data.get_class(s).proprietary_code_tarball()
        if not f:
            continue
        d = pkio.mkdir_parent(
            sirepo.srdb.proprietary_code_dir(s),
        )
        z = d.join(f)
        # POSIT: download/installers/flash-tarball/radiasoft-download.sh
        u = f"{cfg.proprietary_code_uri}/{s}-dev.tar.gz"
        try:
            urllib.request.urlretrieve(u, z)
        except urllib.error.URLError as e:
            if not isinstance(e.reason, FileNotFoundError):
                raise
            pkdlog("uri={} not found; mocking empty file={}", u, z)
            t = d.join("README")
            pkio.write_text(
                t,
                "mocked by sirepo.pkcli.setup_dev",
            )
            subprocess.check_call(
                ["tar", "--create", "--gzip", f"--file={z}", t, "--remove-files"]
            )
