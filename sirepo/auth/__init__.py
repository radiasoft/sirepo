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


#TODO(robnagler) pull these from schema
#: what routeName to return in the event user is logged out in require_user
LOGIN_ROUTE_NAME = 'login'

#: what routeName to return in the event user is logged out in require_user
LOGIN_WITH_ROUTE_NAME = 'loginWith'

COMPLETE_REGISTRATION_ROUTE_NAME = 'completeRegistration'

#: key for auth method for login state
_COOKIE_METHOD = 'sram'

#: There will always be this value in the cookie, if there is a cookie.
_COOKIE_STATE = 'sras'

#: Identifies the user in the cookie
_COOKIE_USER = 'srau'

_STATE_LOGGED_IN = 'li'
_STATE_LOGGED_OUT = 'lo'
_STATE_COMPLETE_REGISTRATION = 'cr'

#: name to module object
_METHOD_MODULES = pkcollections.Dict()

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = 'sirepo_user'

#: uwsgi object for logging
_uwsgi = None

#: allowed_methods + deprecated_methods
valid_methods = []

#: Methods that the user is allowed to see
visible_methods = []


@api_perm.require_cookie_sentinel
def api_authCompleteRegistration():
    # Needs to be explicit, because we would need a special permission
    # for just this API.
    if not _is_logged_in():
        return http_reply.gen_sr_exception(LOGIN_ROUTE_NAME)
    data = http_request.parse_json(assert_sim_type=False)
    dn = _parse_display_name(data)
    uid = _get_user()
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
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    v = pkcollections.Dict(
        displayName=None,
        isCompleteRegistration=s == _STATE_COMPLETE_REGISTRATION,
        isLoggedIn=s == _STATE_LOGGED_IN
        isLoggedOut=s is None or s == _STATE_LOGGED_OUT,
        method=cookie.unchecked_get_value(_COOKIE_METHOD),
        userName=None,
        visibleMethods=visible_methods,
    )
    u = cookie.unchecked_get_value(_COOKIE_USER)
    if v.isLoggedIn:
        m = user_db.UserRegistration.search_by(uid=u)
        if m:
            v.displayName = m.display_name
    if not v.isLoggedOut:
        u.userName = _user_name(v.method, u)
    if pkconfig.channel_in('dev'):
        # useful for testing/debugging
        v.uid = u
    i = int(v.isCompleteRegistration) + int(v.isLoggedIn) + int(v.isLoggedOut)
    assert 1 == i, \
        'sum of isXXX={} but must=1: uid={} v={}'.format(i, u, v)
    return http_reply.render_static(
        'auth-state',
        'js',
        pkcollections.Dict(authState=v),
    )


@api_perm.allow_visitor
def api_logout(simulation_type):
    """Set the current user as logged out.

    Redirects to root simulation page.
    """
    sim_type = sirepo.template.assert_sim_type(simulation_type)
    if _is_logged_in():
        cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
        set_log_user()
    return http_reply.gen_redirect_for_root(sim_type)


def init_apis(app, *args, **kwargs):
    global uri_router, simulation_db, _app
    uri_router = importlib.import_module('sirepo.uri_router')
    simulation_db = importlib.import_module('sirepo.simulation_db')
    assert not _METHOD_MODULES
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


def init_mock(uid='invalid-uid'):
    """A mock user for pkcli"""
    cookie.init_mock()
    _login_user('guest', uid)


def logged_in_user():
    """Get the logged in user

    Returns:
        str: uid of authenticated user
    """
    res = _get_user()
    if not _is_logged_in():
        util.raise_unauthorized('user not logged in uid={}', res)
    assert res, 'no user in cookie: state={} method={}'.format(
        cookie.unchecked_get_value(_COOKIE_STATE),
        cookie.unchecked_get_value(_COOKIE_METHOD),
    )
    return res


def login(module, uid=None, model=None, sim_type=None, **kwargs):
    """Login the user

    Args:
        module (module): method module
        uid (str): user to login
        model (user_db.UserDbBase): user to login (overrides uid)
        sim_type (str): app to redirect to
    Returns:
        flask.Response: reply object or None (if no sim_type)
    """
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
        # We are logged in with a deprecated method, and now the user
        # needs to login with an allowed method.
        return login_failed_redirect(sim_type)
    if not uid:
        # No user in the cookie and method didn't provide one so
        # the user might be switching methods (e.g. github to email or guest to email).
        # Or, this is just a new user, and we'll create one.
        uid = _get_user() if _is_logged_in() else None
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
    return login_success_redirect(sim_type)


def login_failed_redirect(sim_type=None):
    if sim_type:
        return http_reply.gen_redirect_for_local_route(
            sim_type,
            'authorizationFailed',
        )
    util.raise_unauthorized('login failed (without simulation_type)')


def login_success_redirect(sim_type):
    assert sim_type
    return http_reply.gen_redirect_for_root(sim_type)


def process_request(unit_test=None):
    cookie.process_header(unit_test)
    set_log_user()


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
        u = _get_user()
        if m in cfg.deprecated_methods:
            e = 'deprecated'
        else:
            e = 'invalid'
            _reset_state()
        e = 'auth_method={} is {}, forcing login: uid='.format(m, e, u)
    elif s == _STATE_LOGGED_OUT:
        e = 'logged out user={}'.format(_get_user())
        if m in cfg.deprecated_methods:
            # Force login to this specific method so we can migrate to valid method
            r = LOGIN_WITH_ROUTE_NAME
            p = {'authMethod': m}
    elif s == _STATE_COMPLETE_REGISTRATION:
        r = COMPLETE_REGISTRATION_ROUTE_NAME
        e = 'uid={} needs to complete registration'.format(_get_user())
    else:
        cookie.reset_state('state={} invalid, cannot continue'.format(s))
        e = 'invalid cookie'
    pkdlog('user not logged in: {}', e)
    return http_reply.gen_sr_exception(r, p)


def reset_state():
    cookie.unchecked_remove(_COOKIE_USER)
    cookie.unchecked_remove(_COOKIE_METHOD)
    cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
    _set_log_user()


def user_dir_not_found(uid):
    """Called by simulation_db when user_dir is not found

    Deletes any user records

    Args:
        uid (str): user that does not exist
    """
    with user_db.thread_lock:
        for m in _METHOD_MODULES.keys():
            u = m._method_user_model(m, uid)
            if u:
                u.delete()
                u.save()
        u = user_db.UserRegistration.search_by(uid=uid)
        u.delete()
        u.save()
    reset_state()
    util.raise_unauthorized('simulation_db dir not found, deleted uid={}', uid)


def user_if_logged_in(method):
    """Verify user is logged in and method matches

    Args:
        method (str): method must be logged in as
    """
    if not _is_logged_in():
        return None
    m = cookie.unchecked_get_value(_COOKIE_METHOD)
    if m != method:
        return None
    return _get_user()


def _auth_hook_from_header(values):
    """Migrate from old cookie values

    Always sets _COOKIE_STATE, which is our sentinel.

    Args:
        values (dict): just parsed values
    Returns:
        dict: unmodified or migrated values
    """
    if values.get(_COOKIE_STATE):
        # normal case: we've seen a cookie at least once
        return values
    u = values.get('sru') or values.get('uid')
    res = {}
    if not u:
        # normal case: new visitor, and no user/state; set logged out
        # and return all values
        values[_COOKIE_STATE] = _STATE_LOGGED_OUT
        return values
    # Migrate
    o = values.get('sros') or values.get('oauth_login_state')
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
    # Upgrade cookie to current structure. Set the sentinel, too.
    values = {
        _COOKIE_USER: u,
        _COOKIE_METHOD: m,
        _COOKIE_STATE: s,
    }
    cookie.set_sentinel(values)
    pkdlog('migrated cookie={}', values)
    return values


def _get_user():
    if not cookie.has_sentinel():
        util.raise_unauthorized('Missing sentinel, cookies may be disabled')
    return cookie.unchecked_get_value(_COOKIE_USER)


def _is_logged_in():
    """Logged in is either needing to complete registration or done"""
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    return s in (_STATE_COMPLETE_REGISTRATION, _STATE_LOGGED_IN)


def _login_user(module, uid):
    """Set up the cookie for logged in state

    If a deprecated or non-visible method, just login. Otherwise, check the db
    for registration.

    Args:
        module (module): what auth method
        uid (str): which uid

    """
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
    _set_log_user()


def _method_user_model(method, uid):
    m = _METHOD_MODULES[method]
    if not hasattr(m, 'UserModel'):
        return None
    return m.UserModel.search_by(uid=uid)


def _set_log_user():
    if not _uwsgi:
        # Only works for uWSGI (service.uwsgi). sirepo.service.http uses
        # the limited http server for development only. This uses
        # werkzeug.serving.WSGIRequestHandler.log which hardwires the
        # common log format to: '%s - - [%s] %s\n'. Could monkeypatch
        # but we only use the limited http server for development.
        return
    u = _get_user()
    if u:
        u = cookie.unchecked_get_value(_COOKIE_STATE) + '-' + u
    else:
        u = '-'
    _app.uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, u)


def _update_session(login_state, auth_method):
    cookie.set_value(_COOKIE_LOGIN_SESSION, login_state)
    cookie.set_value(_COOKIE_METHOD, auth_method)


def _user_name(*args, **kwargs):
    u = _method_user_model(*args, **kwargs)
    return u and u.user_name


def _validate_method(method):
    if method in valid_methods:
        return None
    pkdlog('invalid auth method={}'.format(method))
    return http_reply.gen_sr_exception(LOGIN_ROUTE_NAME)


cfg = pkconfig.init(
    allowed_methods=(('guest',), tuple, 'for logging in'),
    deprecated_methods=(tuple(), tuple, 'for migrating to allowed_methods'),
)
