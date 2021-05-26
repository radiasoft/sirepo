# -*- coding: utf-8 -*-
u"""Manage global context in threaded (Flask) and non-threaded (Tornado) applications

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
# Limit imports
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import contextlib
import sirepo.events
import sirepo.util

_FLASK_G_SR_CONTEXT_KEY = 'srcontext'

_non_threaded_context = None


@contextlib.contextmanager
def create():
    """Create an srcontext approprieate for our current state (flask or not)

    It is possible to have both _non_threaded_context and flask.g set
    (ex in tests).
    """
    try:
        if sirepo.util.in_flask_request():
            import flask
            assert not flask.g.get(_FLASK_G_SR_CONTEXT_KEY), \
                f'existing srcontext on flask.g={flask.g}'
            flask.g.setdefault(_FLASK_G_SR_CONTEXT_KEY, PKDict())
        else:
            global _non_threaded_context
            assert not _non_threaded_context, \
                'existing _non_threaded_context{_non_threaded_context}'
            _non_threaded_context = PKDict()
        yield _context()
    finally:
        if sirepo.util.in_flask_request():
            import flask
            c = flask.g.pop(_FLASK_G_SR_CONTEXT_KEY)
        else:
            c = _non_threaded_context
            _non_threaded_context = None


def get(key, default=None):
    return _context().get(key, default)


def pop(key, default=None):
    return _context().pop(key, default)


def set(key, value):
    _context()[key] = value


def setdefault(key, default=None):
    return _context().setdefault(key, default)


def _context():
    if sirepo.util.in_flask_request():
        import flask
        return flask.g.get(_FLASK_G_SR_CONTEXT_KEY)
    return _non_threaded_context
