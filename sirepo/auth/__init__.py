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
from sirepo import http_request
from sirepo import auth_db
from sirepo import util
import sirepo.template
import datetime
import importlib


#: what routeName to return in the event user is logged out in require_user
LOGIN_ROUTE_NAME = 'login'

#: Guest is a special method
METHOD_GUEST = 'guest'

#: key for auth method for login state
_COOKIE_METHOD = 'sram'

#: There will always be this value in the cookie, if there is a cookie.
_COOKIE_STATE = 'sras'

#: Identifies the user in the cookie
_COOKIE_USER = 'srau'

_GUEST_USER_DISPLAY_NAME = 'Guest User'

_STATE_LOGGED_IN = 'li'
_STATE_LOGGED_OUT = 'lo'
_STATE_COMPLETE_REGISTRATION = 'cr'

#: name to module object
_METHOD_MODULES = pkcollections.Dict()

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = 'sirepo_user'

#TODO(robnagler) probably from the schema
#: For formatting the size parameter to an avatar_uri
_AVATAR_SIZE = 40

#: uwsgi object for logging
_uwsgi = None

#: methods + deprecated_methods
valid_methods = []

#: Methods that the user is allowed to see
visible_methods = []

#: visible_methods excluding guest
non_guest_methods = []


@api_perm.require_cookie_sentinel
def api_authCompleteRegistration():
    # Needs to be explicit, because we would need a special permission
    # for just this API.
    if not _is_logged_in():
        return http_reply.gen_sr_exception(LOGIN_ROUTE_NAME)
    complete_registration(_parse_display_name(http_request.parse_json()))
    return http_reply.gen_json_ok()


@api_perm.allow_visitor
def api_authState():
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    v = pkcollections.Dict(
        avatarUrl=None,
        displayName=None,
        guestIsOnlyMethod=not non_guest_methods,
        isGuestUser=False,
        isLoggedIn=_is_logged_in(s),
        isLoginExpired=False,
        method=cookie.unchecked_get_value(_COOKIE_METHOD),
        needCompleteRegistration=s == _STATE_COMPLETE_REGISTRATION,
        userName=None,
        visibleMethods=visible_methods,
    )
    u = cookie.unchecked_get_value(_COOKIE_USER)
    if v.isLoggedIn:
        if v.method == METHOD_GUEST:
            # currently only method to expire login
            v.displayName = _GUEST_USER_DISPLAY_NAME
            v.isGuestUser = True
            v.isLoginExpired = _METHOD_MODULES[METHOD_GUEST].is_login_expired()
            v.needCompleteRegistration = False
            v.visibleMethods = non_guest_methods
        else:
            r = auth_db.UserRegistration.search_by(uid=u)
            if r:
                v.displayName = r.display_name
        _method_auth_state(v, u)
    if pkconfig.channel_in('dev'):
        # useful for testing/debugging
        v.uid = u
    return http_reply.render_static(
        'auth-state',
        'js',
        pkcollections.Dict(auth_state=v),
    )


@api_perm.allow_visitor
def api_authLogout(simulation_type=None):
    """Set the current user as logged out.

    Redirects to root simulation page.
    """
    t = None
    if simulation_type:
        try:
            t = sirepo.template.assert_sim_type(simulation_type)
        except AssertionError:
            pass
    if _is_logged_in():
        cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
        _set_log_user()
    return http_reply.gen_redirect_for_root(t)


def complete_registration(name=None):
    """Update the database with the user's display_name and sets state to logged-in.
    Guests will have no name.
    """
    u = _get_user()
    with auth_db.thread_lock:
        r = user_registration(u)
        if cookie.unchecked_get_value(_COOKIE_METHOD) is METHOD_GUEST:
            assert name is None, \
                'Cookie method is {} and name is {}. Expected name to be None'.format(METHOD_GUEST, name)
        r.display_name = name
        r.save()
    cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_IN)


def guest_uids():
    """All of the uids corresponding to guest users."""
    return auth_db.UserRegistration.search_all_for_column('uid', display_name=None)


def init_apis(app, *args, **kwargs):
    global uri_router, simulation_db, _app, cfg
    assert not _METHOD_MODULES

    cfg = pkconfig.init(
        methods=((METHOD_GUEST,), tuple, 'for logging in'),
        deprecated_methods=(tuple(), tuple, 'for migrating to methods'),
    )
    uri_router = importlib.import_module('sirepo.uri_router')
    simulation_db = importlib.import_module('sirepo.simulation_db')
    auth_db.init(app)
    _app = app
    this_module = pkinspect.this_module()
    p = this_module.__name__
    valid_methods.extend(cfg.methods + cfg.deprecated_methods)
    for n in valid_methods:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        uri_router.register_api_module(m)
        _METHOD_MODULES[n] = m
        if m.AUTH_METHOD_VISIBLE and n in cfg.methods:
            visible_methods.append(n)
        setattr(this_module, n, m)
    non_guest_methods.extend([m for m in visible_methods if m != METHOD_GUEST])
    cookie.auth_hook_from_header = _auth_hook_from_header


def init_mock(uid):
    """A mock user for pkcli"""
    cookie.init_mock()
    if uid:
        import sirepo.auth.guest
        _login_user(sirepo.auth.guest, uid)


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
        model (auth_db.UserDbBase): user to login (overrides uid)
        sim_type (str): app to redirect to
    Returns:
        flask.Response: reply object or None (if no sim_type)
    """
    r = _validate_method(module, sim_type=sim_type)
    guest_uid = None
    if r:
        return r
    if model:
        uid = model.uid
        # if previously cookied as a guest, move the non-example simulations into uid below
        m = cookie.unchecked_get_value(_COOKIE_METHOD)
        if m == METHOD_GUEST and module.AUTH_METHOD != METHOD_GUEST:
            guest_uid = _get_user() if _is_logged_in() else None
    if uid:
        _login_user(module, uid)
    if module.AUTH_METHOD in cfg.deprecated_methods:
        pkdlog('deprecated auth method={} uid={}'.format(module.AUTH_METHOD, uid))
        if not uid:
            # No user so clear cookie so this method is removed
            reset_state()
        # We are logged in with a deprecated method, and now the user
        # needs to login with an allowed method.
        return login_fail_redirect(sim_type, module, 'deprecated')
    if not uid:
        # No user in the cookie and method didn't provide one so
        # the user might be switching methods (e.g. github to email or guest to email).
        # Not allowed to go to guest from other methods, because there's
        # no authentication for guest.
        # Or, this is just a new user, and we'll create one.
        uid = _get_user() if _is_logged_in() else None
        m = cookie.unchecked_get_value(_COOKIE_METHOD)
        if uid and module.AUTH_METHOD not in (m, METHOD_GUEST):
            # switch this method to this uid (even for methods)
            # except if the same method, then assuming logging in as different user.
            # This handles the case where logging in as guest, creates a user every time
            _login_user(module, uid)
        else:
            uid = simulation_db.user_create(lambda u: _login_user(module, u))
        if model:
            model.uid = uid
            model.save()
    if sim_type:
        if guest_uid and guest_uid != uid:
            simulation_db.move_user_simulations(guest_uid, uid)
        return login_success_redirect(sim_type)
    # bluesky or basic
    return None


def login_fail_redirect(sim_type=None, module=None, reason=None):
    if sim_type:
        return http_reply.gen_redirect_for_local_route(
            sim_type,
            'loginFail',
            {
                'method': module.AUTH_METHOD,
                'reason': reason,
            },
        )
    util.raise_unauthorized(
        'login failed (no sym_type): reason={} method={}'.format(
            reason,
            module.AUTH_METHOD,
        ),
    )


def login_success_redirect(sim_type):
    if sim_type:
        if cookie.get_value(_COOKIE_STATE) == _STATE_COMPLETE_REGISTRATION:
            if cookie.get_value(_COOKIE_METHOD) == METHOD_GUEST:
                complete_registration()
            else:
                return http_reply.gen_redirect_for_local_route(
                    sim_type,
                    'completeRegistration',
                )
    return http_reply.gen_redirect_for_root(sim_type)


def process_request(unit_test=None):
    cookie.process_header(unit_test)
    _set_log_user()


def require_auth_basic():
    m = _METHOD_MODULES['basic']
    r = _validate_method(m)
    if r:
        return r
    uid = m.require_user()
    if not uid:
        return _app.response_class(
            status=401,
            headers={'WWW-Authenticate': 'Basic realm="*"'},
        )
    cookie.set_sentinel()
    return login(m, uid=uid)


def require_user():
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    e = None
    r = 'login'
    m = cookie.unchecked_get_value(_COOKIE_METHOD)
    p = None
    if s is None:
        e = 'no user in cookie'
    elif s == _STATE_LOGGED_IN:
        if m in cfg.methods:
            return _METHOD_MODULES[m].validate_login()
        u = _get_user()
        if m in cfg.deprecated_methods:
            e = 'deprecated'
        else:
            e = 'invalid'
            reset_state()
        e = 'auth_method={} is {}, forcing login: uid='.format(m, e, u)
    elif s == _STATE_LOGGED_OUT:
        e = 'logged out uid={}'.format(_get_user())
        if m in cfg.deprecated_methods:
            # Force login to this specific method so we can migrate to valid method
            r = 'loginWith'
            p = {':method': m}
    elif s == _STATE_COMPLETE_REGISTRATION:
        if m == METHOD_GUEST:
            complete_registration()
            return None
        r = 'completeRegistration'
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
    with auth_db.thread_lock:
        for m in _METHOD_MODULES.values():
            u = _method_user_model(m, uid)
            if u:
                u.delete()
        u = auth_db.UserRegistration.search_by(uid=uid)
        if u:
            u.delete()
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


def user_registration(uid):
    """Get UserRegistration record or create one

    Args:
        uid (str): registrant
    Returns:
        auth.UserRegistration: record (potentially blank)
    """
    res = auth_db.UserRegistration.search_by(uid=uid)
    if not res:
        res = auth_db.UserRegistration(
            uid=uid,
            created=datetime.datetime.utcnow(),
        )
        res.save()
    return res


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
        # check for cfg.methods changes
        m = values.get(_COOKIE_METHOD)
        if m and m not in valid_methods:
            # invalid method (changed config), reset state
            pkdlog('possibly misconfigured server: invalid cookie_method={}, clearing values={}', values)
            pkcollections.unchecked_del(
                values,
                _COOKIE_METHOD,
                _COOKIE_USER,
                _COOKIE_STATE,
            )
        return values
    u = values.get('sru') or values.get('uid')
    if not u:
        # normal case: new visitor, and no user/state; set logged out
        # and return all values
        values[_COOKIE_STATE] = _STATE_LOGGED_OUT
        return values
    # Migrate
    o = values.get('sros') or values.get('oauth_login_state')
    s = _STATE_COMPLETE_REGISTRATION
    if o is None or o in ('anonymous', 'a'):
        m = METHOD_GUEST
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
    return cookie.unchecked_get_value(_COOKIE_USER)


def _is_logged_in(state=None):
    """Logged in is either needing to complete registration or done

    Args:
        state (str): logged in state [None: from cookie]
    Returns:
        bool: is in one of the logged in states
    """
    s = state or cookie.unchecked_get_value(_COOKIE_STATE)
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
    if module.AUTH_METHOD_VISIBLE and module.AUTH_METHOD in cfg.methods:
        u = user_registration(uid)
        if not u.display_name:
            s = _STATE_COMPLETE_REGISTRATION
    cookie.set_value(_COOKIE_STATE, s)
    _set_log_user()


def _method_auth_state(values, uid):
    if values.method not in _METHOD_MODULES:
        pkdlog('auth state method: "{}" not present in supported methods: {}', values.method, _METHOD_MODULES.keys())
        return
    m = _METHOD_MODULES[values.method]
    u = _method_user_model(m, uid)
    if not u:
        return
    values.userName = u.user_name
    if hasattr(m, 'avatar_uri'):
        values.avatarUrl = m.avatar_uri(u, _AVATAR_SIZE)


def _method_user_model(module, uid):
    if not hasattr(module, 'UserModel'):
        return None
    return module.UserModel.search_by(uid=uid)


def _parse_display_name(data):
    res = data.displayName.strip()
    assert len(res), \
        'invalid post data: displayName={}'.format(data.displayName)
    return res


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


def _validate_method(module, sim_type=None):
    if module.AUTH_METHOD in valid_methods:
        return None
    pkdlog('invalid auth method={}'.format(module.AUTH_METHOD))
    return login_fail_redirect(sim_type, module, 'invalid-method')
