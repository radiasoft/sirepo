# -*- coding: utf-8 -*-
u"""Sirepo events

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import aenum

_HANDLERS = PKDict()


def emit(event, kwargs):
    for h in _HANDLERS[event]:
        h(kwargs or PKDict())


def register(registrants):
    for k, v in registrants.items():
        if v not in _HANDLERS[k]:
            _HANDLERS[k].append(v)


def _init():
    for k in _Kind:
        _HANDLERS[k.value] = []


@aenum.unique
class _Kind(aenum.Enum):
    AUTH_LOGOUT = 'auth_logout'
    END_API_CALL = 'end_api_call'
    GITHUB_AUTHORIZED = 'github_authorized'

_init()
