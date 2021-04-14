# -*- coding: utf-8 -*-
u"""Test sirepo.cookie

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from sirepo import srunit
import pytest

@srunit.wrap_in_request(want_user=False)
def test_set_get():
    from pykern import pkunit, pkcompat
    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp
    from sirepo import cookie

    with cookie.process_header('x'):
        with pkunit.pkexcept('KeyError'):
            cookie.get_value('hi1')
        with pkunit.pkexcept('AssertionError'):
            cookie.set_value('hi2', 'hello')
        pkeq(None, cookie.unchecked_get_value('hi3'))


def test_cookie_outside_of_flask_request():
    from pykern import pkcompat
    from pykern.pkunit import pkeq
    from sirepo import cookie
    from sirepo import srunit

    with srunit.srcontext(), \
         cookie.set_cookie_outside_of_flask_request():
        cookie.set_value('hi4', 'hello')
        r = _Response(status_code=200)
        cookie.save_to_cookie(r)
        pkeq('sirepo_dev', r.args[0])
        pkeq(False, r.kwargs['secure'])
        pkeq('hello', cookie.get_value('hi4'))
        cookie.unchecked_remove('hi4')
        pkeq(None, cookie.unchecked_get_value('hi4'))
        # Nest cookie contexts
        with cookie.process_header(
            'sirepo_dev={}'.format(pkcompat.from_bytes(r.args[1])),
        ):
            pkeq('hello', cookie.get_value('hi4'))

class _Response(PKDict):
    def set_cookie(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
