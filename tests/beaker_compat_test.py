# -*- coding: utf-8 -*-
u"""Test sirepo.beaker_compat

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def _test_cookie(filename, header, uid):
    import shutil
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp
    from sirepo import sr_unit
    sr_unit.flask_client({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'oauth',
        'SIREPO_OAUTH_GITHUB_KEY': 'n/a',
        'SIREPO_OAUTH_GITHUB_SECRET': 'n/a',
        'SIREPO_OAUTH_GITHUB_CALLBACK_URI': 'n/a',
    })

    from sirepo import cookie
    import flask
    cookie.init_mock()
    target = sr_unit.server.cfg.db_dir.join(
        'beaker', 'container_file', filename[0:1], filename[0:2], filename)
    from sirepo import server
    pkio.mkdir_parent_only(target)
    shutil.copy(str(pkunit.data_dir().join(filename)), str(target))
    try:
        del flask.g['sirepo_cookie']
    except KeyError:
        pass
    cookie.init(header)
    pkeq(uid, cookie.get_user(checked=False))


def test_anonymous_user():
    _test_cookie(
        '978f20c7f29a4838a9f16c0dbc61d044.cache',
        'net.sirepo.first_visit=1535555450168; net.sirepo.get_started_notify=1535555451699; sr_cookieconsent=dismiss; net.sirepo.sim_list_view=true; net.sirepo.login_notify_timeout=1535742744032; sirepo_dev=9240a807fbfde9841c278b7f5eb580a7933663a5978f20c7f29a4838a9f16c0dbc61d044',
        'mshw0FdP',
    )
    from pykern.pkunit import pkeq
    from sirepo import cookie
    pkeq('a', cookie.get_value('sros'))


def xtest_no_user():
    _test_cookie(
        'eff2360ca9184155a6757ac096f9d44c.cache',
        'net.sirepo.first_visit=1535555450168; net.sirepo.get_started_notify=1535555451699; sr_cookieconsent=dismiss; net.sirepo.sim_list_view=true; net.sirepo.login_notify_timeout=1535742744032; sirepo_dev=dd68627088f9d783ab32c3a0a63797cc170a80ebeff2360ca9184155a6757ac096f9d44c',
        None,
    )
    from pykern.pkunit import pkeq
    from sirepo import cookie
    pkeq(False, cookie.has_key('sros'))


def xtest_oauth_user():
    _test_cookie(
        'daaf2aa83ac34f65b42102389c4ff11f.cache',
        'sirepo_dev=2f4adb8e95a2324a12f9607b2347ecbce93463bddaaf2aa83ac34f65b42102389c4ff11f; net.sirepo.first_visit=1535736574400; net.sirepo.get_started_notify=1535736579192; sr_cookieconsent=dismiss; net.sirepo.login_notify_timeout=1535746957193',
        'S0QmCORV')
    from pykern.pkunit import pkeq
    from sirepo import cookie
    import flask
    pkeq('li', cookie.get_value('sros'))
    pkeq('moellep', cookie.get_value('sron'))
