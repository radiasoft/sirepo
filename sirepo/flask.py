# -*- coding: utf-8 -*-
"""wrapper for flask

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp

_log_not_flask = _log_not_request = 0

_app = None


def app():
    return _app


def g():
    return flask.g


def in_request():
    # These are globals but possibly accessed from a threaded context. That is
    # desired so we limit logging between all threads.
    # The number 10 below doesn't need to be exact. Just something greater than
    # "a few" so we see logging once the app is initialized and serving requests.
    global _log_not_flask, _log_not_request

    f = sys.modules.get("flask")
    if not f:
        if _log_not_flask < 10:
            _log_not_flask += 1
            pkdlog("flask is not imported")
        return False
    if not f.request:
        if _log_not_request < 10:
            _log_not_request += 1
            if is_server:
                # This will help debug https://github.com/radiasoft/sirepo/issues/3727
                pkdlog("flask.request is False")
        return False
    return True


def send_file(*args, **kwargs):
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
    a.sirepo_uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, u)


def init_module(_in_app=True):
    """Override some functions unless we are in flask"""
    import flask

    if not in_flask:
        global in_flask_request, flask_app
        in_flask_request = lambda: False
        flask_app = lambda: None
