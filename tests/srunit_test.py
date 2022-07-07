# -*- coding: utf-8 -*-
u"""Test sirepo.srunit

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_wrap_in_request():
    s = dict(b=None, f=None, fc=None)
    import sirepo.util

    def b(fc):
        s['fc'] = fc
        if s['b']:
            raise getattr(sirepo.util, s['b'])('b-hello')

    import sirepo.srunit
    @sirepo.srunit.wrap_in_request(sim_types='srw', before_request=b)
    def f():
        if s['f']:
            raise getattr(sirepo.util, s['f'])('f-hello')

    f()

    import pykern.pkunit
    import flask

    with pykern.pkunit.pkexcept('error.*f-hello'):
        s['f'] = 'UserAlert'
        f()
    with pykern.pkunit.pkexcept('error.*b-hello'):
        s['b'] = 'UserAlert'
        f()
