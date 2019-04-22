# -*- coding: utf-8 -*-
u"""Test sirepo.beaker_compat

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_anonymous_user():
    _test_cookie(
        '978f20c7f29a4838a9f16c0dbc61d044.cache',
        'net.sirepo.first_visit=1535555450168; net.sirepo.get_started_notify=1535555451699; sr_cookieconsent=dismiss; net.sirepo.sim_list_view=true; net.sirepo.login_notify_timeout=1535742744032; sirepo_dev=9240a807fbfde9841c278b7f5eb580a7933663a5978f20c7f29a4838a9f16c0dbc61d044',
        'mshw0FdP',
        (
            ('cr', 'sras'),
            ('guest', 'sram'),
        ),
    )


def test_no_user():
    _test_cookie(
        'eff2360ca9184155a6757ac096f9d44c.cache',
        'net.sirepo.first_visit=1535555450168; net.sirepo.get_started_notify=1535555451699; sr_cookieconsent=dismiss; net.sirepo.sim_list_view=true; net.sirepo.login_notify_timeout=1535742744032; sirepo_dev=dd68627088f9d783ab32c3a0a63797cc170a80ebeff2360ca9184155a6757ac096f9d44c',
        None,
        (
            (None, 'sram'),
            (None, 'sras'),
        ),
    )


def test_oauth_user():
    _test_cookie(
        'daaf2aa83ac34f65b42102389c4ff11f.cache',
        'sirepo_dev=2f4adb8e95a2324a12f9607b2347ecbce93463bddaaf2aa83ac34f65b42102389c4ff11f; net.sirepo.first_visit=1535736574400; net.sirepo.get_started_notify=1535736579192; sr_cookieconsent=dismiss; net.sirepo.login_notify_timeout=1535746957193',
        'S0QmCORV',
        (
            ('cr', 'sras'),
            ('github', 'sram'),
        ),
    )


def _test_cookie(filename, header, uid, cases):
    import shutil
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp
    from sirepo import srunit

    def _before_request(fc):
        target = srunit.server._app.sirepo_db_dir.join(
            'beaker', 'container_file', filename[0:1], filename[0:2], filename)
        pkio.mkdir_parent_only(target)
        shutil.copy(str(pkunit.data_dir().join(filename)), str(target))
        for h in header.split('; '):
            x = h.split('=')
            fc.set_cookie('', *x)

    def _op():
        from sirepo import cookie
        from sirepo import auth

        pkeq(uid, auth._get_user())
        for expect, key in cases:
            if expect is None:
                pkeq(False, cookie.has_key(key))
            else:
                pkeq(expect, cookie.unchecked_get_value(key))

    srunit.test_in_request(
        op=_op,
        cfg={
            'SIREPO_AUTH_ALLOW_METHODS': 'oauth',
            'SIREPO_AUTH_GITHUB_KEY': 'n/a',
            'SIREPO_AUTH_GITHUB_SECRET': 'n/a',
            'SIREPO_AUTH_GITHUB_CALLBACK_URI': 'n/a',
        },
        before_request=_before_request,
        want_cookie=False,
    )
