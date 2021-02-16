# -*- coding: utf-8 -*-
u"""Manage global context in threaded (Flask) and non-threaded (Tornado) applications

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import sirepo.util

_FLASK_G_SR_CONTEXT_KEY = 'srcontext'

_NON_THREADED_CONTEXT = PKDict()


def get(key, default=None):
    return _context().get(key, default)


def pop(key, default=None):
    return _context().pkdel(key, default)


def set(key, value):
    _context()[key] = value


def setdefault(key, default=None):
    return _context().setdefault(key, default)


def _context():
    if sirepo.util.in_flask_request():
        import flask
        return flask.g.setdefault(_FLASK_G_SR_CONTEXT_KEY, default=PKDict())
    return _NON_THREADED_CONTEXT
