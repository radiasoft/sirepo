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
    """Get proprietary tarballs and put it in the proprietary code dir

    Args:
      uri (str): where to get tarball (file:// or http://)
    """
    import sirepo.feature_config
    import sirepo.sim_data
    import sirepo.srdb
    import urllib.error
    import urllib.request

    for s in sirepo.feature_config.cfg().proprietary_sim_types:
        f = sirepo.sim_data.get_class(s).proprietary_code_tarball()
        if not f:
            return
        r = pkio.mkdir_parent(
            sirepo.srdb.proprietary_code_dir(s),
        ).join(f)
        # POSIT: download/installers/rpm-code/dev-build.sh
        # TODO(e-carlin): need to fix all of the rsconf code and install code to now handle tarballs
        # manually moving files for now
        u = f'{cfg.proprietary_code_uri}/{f}'
        try:
            urllib.request.urlretrieve(u, r)
        except urllib.error.URLError as e:
            if not isinstance(e.reason, FileNotFoundError):
                raise
            pkdlog('uri={} not found; mocking empty rpm={}', u, r)
            pkio.write_text(
                r,
                'mocked by sirepo.pkcli.setup_dev',
            )
