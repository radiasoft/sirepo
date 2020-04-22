# -*- coding: utf-8 -*-
u"""Test sirepo.cookie

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from sirepo import srunit

@srunit.wrap_in_request(want_user=False)
def test_set_get():
    from pykern import pkunit, pkcompat
    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp
    from pykern import pkcollections
    from sirepo import cookie

    class _Response(pkcollections.Dict):
        def set_cookie(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    cookie.process_header('x')
    with pkunit.pkexcept('KeyError'):
        cookie.get_value('hi1')
    with pkunit.pkexcept('AssertionError'):
        cookie.set_value('hi2', 'hello')
    pkeq(None, cookie.unchecked_get_value('hi3'))
    cookie.set_cookie_for_utils()
    cookie.set_value('hi4', 'hello')
    r = _Response(status_code=200)
    cookie.save_to_cookie(r)
    pkeq('sirepo_dev', r.args[0])
    pkeq(False, r.kwargs['secure'])
    pkeq('hello', cookie.get_value('hi4'))
    cookie.unchecked_remove('hi4')
    pkeq(None, cookie.unchecked_get_value('hi4'))
    cookie.process_header(
        'sirepo_dev={}'.format(pkcompat.from_bytes(r.args[1])),
    )
    pkeq('hello', cookie.get_value('hi4'))
