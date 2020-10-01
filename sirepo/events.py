# -*- coding: utf-8 -*-
u"""Sirepo events

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
import enum

class _AutoName(enum.Enum):
    def _generate_next_value_(name, *args):
        return name


class Type(_AutoName):
    AUTH_LOGOUT = enum.auto()
    END_API_CALL = enum.auto()
    GITHUB_AUTHORIZED = enum.auto()


_HANDLERS = PKDict()


def emit(event, kwargs=None):
    for h in _HANDLERS[event]:
        if kwargs:
            h(kwargs)
        else:
            h()


def init():
    for t in Type:
        _HANDLERS[t] = []


def register(registrants):
    for r in registrants:
        _HANDLERS[r].append(registrants[r])
