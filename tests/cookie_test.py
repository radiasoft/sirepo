# -*- coding: utf-8 -*-
u"""Test sirepo.cookie

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkcollections


def test_1():
    import shutil
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    srunit.flask_client()

    from sirepo import cookie
    cookie.init_mock()
    cookie.init('x')
    with pkunit.pkexcept('Forbidden'):
        cookie.get_user()
    with pkunit.pkexcept('Forbidden'):
        cookie.get_user(checked=False)
    cookie.set_sentinel()
    cookie.set_user('abc')
    cookie.set_value('hi', 'hello')
    r = _Response(status_code=200)
    cookie.save_to_cookie(r)
    pkeq('sirepo_dev', r.args[0])
    pkeq(False, r.kwargs['secure'])
    pkeq('abc', cookie.get_user())
    cookie.clear_user()
    cookie.unchecked_remove('hi')
    pkeq(None, cookie.get_user(checked=False))
    cookie.init('sirepo_dev={}'.format(r.args[1]))
    pkeq('hello', cookie.get_value('hi'))
    pkeq('abc', cookie.get_user())


class _Response(pkcollections.Dict):

    def set_cookie(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
