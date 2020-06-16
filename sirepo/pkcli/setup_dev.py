# -*- coding: utf-8 -*-
u"""setup development directory

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkconfig
from pykern import pkio
import pathlib


def default_command():
    global cfg

    assert pkconfig.channel_in('dev'), \
        'Only to be used in dev. channel={}'.format(pkconfig.cfg.channel)
    cfg = pkconfig.init(
        proprietary_code_uri=(
            f'file://{pathlib.Path.home()}/src/radiasoft/rsconf/rpm',
            str,
            'root uri of RPMs',
        ),
    )
    _proprietary_codes()


def _proprietary_codes():
    """Get proprietary RPMs and put it in the proprietary code dir

    Args:
      uri (str): where to get RPM (file:// or http://)
    """
    import urllib.request
    import sirepo.feature_config
    import sirepo.srdb
    import sirepo.sim_data

    for s in sirepo.feature_config.cfg().proprietary_sim_types:
        d = sirepo.srdb.proprietary_code_dir(s)
        if d.exists():
            continue
        urllib.request.urlretrieve(
            # POSIT: download/installers/rpm-code/dev-build.sh
            f'{cfg.proprietary_code_uri}/rscode-{s}-dev.rpm',
            pkio.mkdir_parent(d).join(
                sirepo.sim_data.get_class(s).proprietary_code_rpm(),
            ),
        )
