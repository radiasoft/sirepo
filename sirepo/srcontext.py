# -*- coding: utf-8 -*-
"""Manage global context in threaded (Flask) and non-threaded (Tornado) applications

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
# Limit imports
from pykern.pkcollections import PKDict
import contextlib
import sirepo.util

_self = _Base()

def singleton():
    """Shared context

    Returns:
        object: global context instance
    """
    return _self


def init_for_flask():
    global _self
    if not _self:
        _self = _FlaskContext()


class _Async(PKDict):
    def __enter(self):
        # could assert items
        return None

    def __exit__(self):
        self.clear()
        return False


class _Flask:
    def __enter(self):
        assert not flask.g.get(
            _FLASK_G_SR_CONTEXT_KEY
        ), f"existing srcontext on flask.g={flask.g}"
        flask.g.setdefault(_FLASK_G_SR_CONTEXT_KEY, PKDict())
        return None

    def __exit__(self, *args, **kwargs):
        return False

    def get

    if sirepo.util.in_flask_request():
        return _self
    return
    try:
            _flask_push()
        else:
            global _non_threaded_context
            assert (
                not _non_threaded_context
            ), "existing _non_threaded_context{_non_threaded_context}"
            _non_threaded_context = PKDict()
        yield _context()
    finally:
        if sirepo.util.in_flask_request():
            _flask_pop()
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
        return _FlaskContext()
        import flask

        c = flask.g.get(_FLASK_G_SR_CONTEXT_KEY)
        if c is None:
            raise AssertionError("no flask.g {_FLASK_G_SR_CONTEXT_KEY}")
        return c
    c = _non_threaded_context
    if c is None:
        raise AssertionError("no _non_threaded_context")
    return c


def _flask_push():
    import flask



def _flask_pop():
    import flask

    c = flask.g.pop(_FLASK_G_SR_CONTEXT_KEY)
