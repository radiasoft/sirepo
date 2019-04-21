# -*- coding: utf-8 -*-
u"""Test sirepo.cookie

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from sirepo import srunit

@srunit.wrap_in_request()
def test_set_get():
    from pykern import pkunit
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
        cookie.get_value('hi')
    with pkunit.pkexcept('AssertionError'):
        cookie.set_value('hi', 'hello')
    pkeq(None, cookie.unchecked_get_value('hi'))
    cookie.init_mock()
    cookie.set_value('hi', 'hello')
    r = _Response(status_code=200)
    cookie.save_to_cookie(r)
    pkeq('sirepo_dev', r.args[0])
    pkeq(False, r.kwargs['secure'])
    pkeq('hello', cookie.get_value('hi'))
    cookie.unchecked_remove('hi')
    pkeq(None, cookie.unchecked_get_value('hi'))
    cookie.process_header('sirepo_dev={}'.format(r.args[1]))
    pkeq('hello', cookie.get_value('hi'))
