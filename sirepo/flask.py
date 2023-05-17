# -*- coding: utf-8 -*-
"""wrapper for flask

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp

_log_not_request = 0

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = "sirepo_user"

_initialized = None

is_server = False

flask = None

_app = None


def app():
    _assert_flask()
    return _app


def app_set(app):
    global _app
    assert _app is None
    _app = app


def in_request():
    if not flask:
        return False
    if not flask.request:
        global _log_not_request

        if is_server and _log_not_request < 10:
            _log_not_request += 1
            # This will help debug https://github.com/radiasoft/sirepo/issues/3727
            pkdlog("flask.request is False")
        return False
    return True


def send_file(*args, **kwargs):
    _assert_flask()
    return flask.send_file(*args, **kwargs)


def set_log_user(user_op):
    if not in_request():
        return
    a = app()
    if not a or not a.sirepo_uwsgi:
        # Only works for uWSGI (service.uwsgi). sirepo.service.http uses
        # the limited http server for development only. This uses
        # werkzeug.serving.WSGIRequestHandler.log which hardwires the
        # common log format to: '%s - - [%s] %s\n'. Could monkeypatch
        # but we only use the limited http server for development.
        return
    a.sirepo_uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, user_op())


def init_module(want_flask):
    """Override some functions unless we are in flask"""
    global _initialized, flask

    if _initialized:
        return
    _initialized = True
    if want_flask:
        import flask


def _assert_flask():
    if not flask:
        raise AssertionError("called outside Flask")
