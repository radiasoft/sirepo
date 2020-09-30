# -*- coding: utf-8 -*-
u"""Sirepo events

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict

GITHUB_AUTHORIZED = 'github_authorized'

_EVENTS = (GITHUB_AUTHORIZED, )

_HANDLERS = PKDict()


def emit(event, kwargs):
    for h in _HANDLERS[event]:
        h(kwargs)


def init():
    for e in _EVENTS:
        _HANDLERS[e] = []


def register(event, handler):
    _HANDLERS[event].append(handler)
