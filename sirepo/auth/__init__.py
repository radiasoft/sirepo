# -*- coding: utf-8 -*-
u"""Authentication

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from sirepo import api_perm
from sirepo import cookie
from sirepo import http_reply
from sirepo import user_db
from sirepo import util
import flask
import importlib


#: what routeName to return in the event user is logged out in require_user
LOGIN_ROUTE_NAME = 'login'

#: what routeName to return in the event user is logged out in require_user
LOGIN_WITH_ROUTE_NAME = 'loginWith'

COMPLETE_REGISTRATION_ROUTE_NAME = 'completeRegistration'

#: There will always be this value in the cookie, if there is a cookie.
_COOKIE_STATE = 'sras'

_STATE_LOGGED_IN = 'li'
_STATE_LOGGED_OUT = 'li'
_STATE_COMPLETE_REGISTRATION = 'cr'

#: key for auth method for login state
_COOKIE_METHOD = 'sram'

#: Identifies the user in the cookie
_COOKIE_USER = 'sru'

#: initialized modules (for "basic" and so they don't get garbaged collected)
_METHOD_MODULES = pkcollections.Dict()

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = 'sirepo_user'

#: uwsgi object for logging
_uwsgi = None

#: allowed_methods + deprecated_methods
valid_methods = []

#: Methods that the user is allowed to see
visible_methods = []


@api_perm.require_user
def api_authCompleteRegistration():
    data = http_request.parse_json(assert_sim_type=False)
    dn = _parse_display_name(data)
    uid = get_user()
    assert is_logged_in(), \
        'user is not logged in, uid={}'.format(uid)
    with user_db.thread_lock:
        u = User.search_by(uid=uid)
        if not u:
            # first time for this user
            u = User(uid=uid)
        u.display_name = dn
        u.save()
    return http_reply.gen_json_ok()


@api_perm.allow_visitor
def api_authState():
    allowed_methods can only include visible methods, not bluesky and basic_auth
    a = cookie.unchecked_get_value(_COOKIE_METHOD, _AUTH_METHOD_ANONYMOUS_COOKIE_VALUE)
    s = cookie.unchecked_get_value(_COOKIE_LOGIN_SESSION, _LOGGED_OUT)
    v = pkcollections.Dict(
        user_state = pkcollections.Dict(
            authMethod=_AUTH_METHOD_ANONYMOUS_MODULE_NAME,
            displayName=None,
            loginSession=_LOGIN_SESSION_MAP[s],
            userName=None,
        ),
        is_logged_out=s == _LOGGED_OUT,
    )
    if login_module:
        v.user_state.authMethod = login_module.AUTH_METHOD
        if pkconfig.channel_in('dev'):
            # useful for testing/debugging
            v.user_state.uid  = cookie.unchecked_get_user()
        if a == login_module.AUTH_METHOD_COOKIE_VALUE and s == _LOGGED_IN:
            u = login_module.UserModel.search_by(uid=get_user())
            if u:
                v.user_state.update(
                    displayName=u.display_name,
                    userName=u.user_name,
                )
    return http_reply.render_static('user-state', 'js', v)


@api_perm.allow_visitor
def api_logout(simulation_type):
    """Set the current user as logged out.
    """
    if has_user_value():
        logout()
    return flask.redirect('/{}'.format(simulation_type))


def has_user_value():
    return bool(cookie.has_key(_COOKIE_USER) and get_value(_COOKIE_USER))


def init_mock(uid='invalid-uid'):
    """A mock user for pkcli"""
    cookie.init_mock()
    set_user(uid)


def init_apis(app, *args, **kwargs):
    global uri_router, simulation_db, _app
    uri_router = importlib.import_module('sirepo.uri_router')
    simulation_db = importlib.import_module('sirepo.simulation_db')
    assert not _METHOD_CLASS
    _app = app
    p = pkinspect.this_module().__name__
    valid_methods.extend(cfg.allowed_methods + cfg.deprecated_methods)
    for n in valid_methods:
        m = importlib.import_module(pkinspect.module_name_join(p, n))
        uri_router.register_api_module(m)
        _METHOD_MODULES[n] = m
        if m.AUTH_METHOD_VISIBLE and n in cfg.allowed_methods:
            visible_methods.append(n)
    cookie.auth_hook_from_header = _auth_hook_from_header


def get_user_if_logged_in(method=None):
    """Verify user is logged in and method matches

    Args:
        method (str): method must be logged in as [None]
    """
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    if s not in (_STATE_COMPLETE_REGISTRATION, _STATE_LOGGED_IN):
        return None
    if method:
        m = cookie.unchecked_get_value(_COOKIE_METHOD)
        if m != method:
            return None
    return get_user()


def login(module, uid=None, model=None, sim_type=None, **kwargs):
    r = _validate_method(module.AUTH_METHOD):
    if r:
        return r
    if model:
        uid = model.uid
    if uid:
        _login_user(module, uid)
    if module.AUTH_METHOD in cfg.deprecated_methods:
        pkdlog('deprecated auth method={} uid={}'.format(module.AUTH_METHOD, uid))
        if not uid:
            # No user so clear cookie so this method is removed
            _reset_state()
        # login with a non-deprecated method
        return http_reply.gen_sr_exception(LOGIN_ROUTE_NAME)
    if not uid:
        uid = get_user_if_logged_in()
        m = cookie.get_value(_COOKIE_METHOD)
        if uid and m != module.AUTH_METHOD
            # switch this method to this uid (even for allowed_methods)
            # except if the same method, then assuming logging in as different user.
            # This handles the case where logging in as guest, creates a user every time
            _login_user(module, uid)
        else:
            uid = simulation_db.user_create(lambda u: _login_user(module, u))
        if model:
            model.uid = uid
            model.save()
    if not sim_type:
        return None
    s = simulation_db.get_schema(sim_type)
    #TODO(pjm): need uri_router method for this?
    return server.javascript_redirect(
        '/{}#{}'.format(
            sim_type,
            s.localRoutes.authorizationFailed.route,
        ),
    )


def login_as_user(user, module):
    prev_uid = unchecked_get_user()
    if prev_uid and prev_uid != user.uid:
        # check if prev_uid is already in the
        # user database, if not, copy over simulations
        # from anonymous to this user.
        if not user.search_by(uid=prev_uid):
            simulation_db.move_user_simulations(
                prev_uid,
                user.uid,
            )
        set_user(user.uid)
    _update_session(_LOGGED_IN, module.AUTH_METHOD_COOKIE_VALUE)


def logout_as_user(module):
    _update_session(_LOGGED_OUT, module.AUTH_METHOD_COOKIE_VALUE)


def process_request(unit_test=None):
    cookie.process_header(unit_test)
    _migrate_cookie_keys()
    if has_user_value():
        set_log_user(unchecked_get_user())


def require_auth_basic():
    r = _validate_method('basic')
    if r:
        return r
    m = _METHOD_MODULES['basic']
    uid = m.require_user()
    if not uid:
        return _app.response_class(
            status=401,
            headers={'WWW-Authenticate': 'Basic realm="*"'},
        )
    return login(m, uid=uid)


def require_user():
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    e = None
    r = LOGIN_ROUTE_NAME
    m = cookie.unchecked_get_value(_COOKIE_METHOD)
    p = None
    if s is None:
        e = 'no user in cookie'
    elif s == _STATE_LOGGED_IN:
        if m in cfg.allowed_methods:
            # Success
            return None
        u = get_user()
        if m in cfg.deprecated_methods:
            e = 'deprecated'
        else:
            e = 'invalid'
            _reset_state()
        e = 'auth_method={} is {}, forcing login: uid='.format(m, e, u)
    elif s == _STATE_LOGGED_OUT:
        e = 'logged out user={}'.format(unchecked_get_user())
        if m in cfg.deprecated_methods:
            # Force login to this specific method so we can migrate to valid method
            r = LOGIN_WITH_ROUTE_NAME
            p = {'authMethod': m}
    elif s == _STATE_COMPLETE_REGISTRATION:
        r = COMPLETE_REGISTRATION_ROUTE_NAME
        e = 'uid={} needs to complete registration'.format(get_user())
    else:
        cookie.reset_state('state={} invalid, cannot continue'.format(s))
        e = 'invalid cookie'
    pkdlog('user not logged in: {}', e)
    return http_reply.gen_sr_exception(r, p)


def get_user():
    return _get_user(True)


def reset_state():
    set_log_user(None)
    cookie.unchecked_remove(_COOKIE_USER)
    cookie.unchecked_remove(_COOKIE_METHOD)
    cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)


def unchecked_get_user():
    _get_user(False)


def user_not_found(uid):
    no directory or not found in db?
    Force user to logout and log back in
    force a logout by throwing an srexception?


def _auth_hook_from_header(values):
    """Migrate from old cookie values

    Always sets _COOKIE_STATE, which is our sentinel.

    Args:
        values (dict): just parsed values
    Returns:
        dict: unmodified or migrated values
    """
    if values.get(_COOKIE_STATE):
        # normal logged in case
        return values
    u = values.get('sru', values.get('uid'))
    if not u:
        # no user, so probably visitor case
        values[_COOKIE_STATE] = _STATE_LOGGED_OUT
        return values
    o = values.get('sros', values.get('oauth_login_state'))
    s = _STATE_COMPLETE_REGISTRATION
    if o is None or o in ('anonymous', 'a'):
        m = 'guest'
    elif o in ('logged_in', 'li', 'logged_out', 'lo'):
        m = 'github'
        if 'i' not in o:
            s = _STATE_LOGGED_OUT
    else:
        pkdlog('unknown cookie values, clearing, not migrating: {}', values)
        return {}
    return {
        _COOKIE_USER: u,
        _COOKIE_METHOD: m,
        _COOKIE_STATE: s,
    }


def _get_user(checked=True):
    if not cookie.has_sentinel():
        util.raise_unauthorized('Missing sentinel, cookies may be disabled')
    return cookie.get_value(_COOKIE_USER) if checked else cookie.unchecked_get_value(_COOKIE_USER)


def _login_user(module, uid):
    # not logged in, but in cookie(?)
    cookie.set_value(_COOKIE_USER, uid)
    cookie.set_value(_COOKIE_METHOD, module.AUTH_METHOD)
    s = _STATE_LOGGED_IN
    if module.AUTH_METHOD_VISIBLE and module.AUTH_METHOD in cfg.allowed_methods:
        ur = user_db.UserRegistration.search_by(uid=uid)
        if not ur:
            ur = user_db.UserRegistration(uid=uid, created=datetime.now())
            ur.save()
        if not ur.display_name:
            s = _STATE_COMPLETE_REGISTRATION
    cookie.set_value(_COOKIE_STATE, s)
    set_log_user(uid)


def _set_log_user(uid):
    if not _uwsgi:
        # Only works for uWSGI (service.uwsgi). sirepo.service.http uses
        # the limited http server for development only. This uses
        # werkzeug.serving.WSGIRequestHandler.log which hardwires the
        # common log format to: '%s - - [%s] %s\n'. Could monkeypatch
        # but we only use the limited http server for development.
        return
    u = 'li-' + uid if uid else '-'
    _app.uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, u)


def _update_session(login_state, auth_method):
    cookie.set_value(_COOKIE_LOGIN_SESSION, login_state)
    cookie.set_value(_COOKIE_METHOD, auth_method)


def _validate_method(method):
    if method in valid_methods:
        return None
    pkdlog('invalid auth method={}'.format(method))
    return http_reply.gen_sr_exception(LOGIN_ROUTE_NAME)


cfg = pkconfig.init(
    allowed_methods=(('guest',), tuple, 'for logging in'),
    deprecated_methods=(tuple(), tuple, 'for migrating to allowed_methods'),
)
