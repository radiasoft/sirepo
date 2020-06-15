# -*- coding: utf-8 -*-
u"""Authentication

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth_db
from sirepo import cookie
from sirepo import http_reply
from sirepo import http_request
from sirepo import job
from sirepo import util
import contextlib
import datetime
import importlib
import sirepo.feature_config
import sirepo.template
import sirepo.uri
import werkzeug.exceptions


#: what routeName to return in the event user is logged out in require_user
LOGIN_ROUTE_NAME = 'login'

#: Guest is a special method
METHOD_GUEST = 'guest'

ROLE_ADM = 'adm'
ROLE_PREMIUM = 'premium'

PAID_USER_ROLES = (ROLE_PREMIUM,)

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

#: methods + deprecated_methods
valid_methods = None

#: Methods that the user is allowed to see
visible_methods = None

#: visible_methods excluding guest
non_guest_methods = None

@api_perm.require_cookie_sentinel
def api_authCompleteRegistration():
    # Needs to be explicit, because we would need a special permission
    # for just this API.
    if not _is_logged_in():
        raise util.SRException(LOGIN_ROUTE_NAME, None)
    complete_registration(
        _parse_display_name(http_request.parse_json().get('displayName')),
    )
    return http_reply.gen_json_ok()


@api_perm.allow_visitor
def api_authState():
    return http_reply.render_static('auth-state', 'js', PKDict(auth_state=_auth_state()))


@api_perm.allow_visitor
def api_authLogout(simulation_type=None):
    """Set the current user as logged out.

    Redirects to root simulation page.
    """
    req = None
    if simulation_type:
        try:
            req = http_request.parse_params(type=simulation_type)
        except AssertionError:
            pass
    if _is_logged_in():
        cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
        _set_log_user()
    return http_reply.gen_redirect_for_app_root(req and req.type)


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


def get_all_roles():
    return [
        role_for_sim_type(t) for t in sirepo.feature_config.cfg().proprietary_sim_types
    ] + [
        ROLE_ADM,
        ROLE_PREMIUM,
    ]


def guest_uids():
    """All of the uids corresponding to guest users."""
    return auth_db.UserRegistration.search_all_for_column('uid', display_name=None)


def init_apis(*args, **kwargs):
    global uri_router, simulation_db, visible_methods, valid_methods, non_guest_methods
    assert not _METHOD_MODULES

    assert not cfg.logged_in_user, \
        'Do not set $SIREPO_AUTH_LOGGED_IN_USER in server'
    uri_router = importlib.import_module('sirepo.uri_router')
    simulation_db = importlib.import_module('sirepo.simulation_db')
    auth_db.init()
    p = pkinspect.this_module().__name__
    visible_methods = []
    valid_methods = cfg.methods.union(cfg.deprecated_methods)
    for n in valid_methods:
        m = importlib.import_module(pkinspect.module_name_join((p, n)))
        uri_router.register_api_module(m)
        _METHOD_MODULES[n] = m
        if m.AUTH_METHOD_VISIBLE and n in cfg.methods:
            visible_methods.append(n)
    visible_methods = tuple(sorted(visible_methods))
    non_guest_methods = tuple(m for m in visible_methods if m != METHOD_GUEST)
    cookie.auth_hook_from_header = _auth_hook_from_header


def is_premium_user():
    return check_user_has_role(ROLE_PREMIUM, raise_forbidden=False)


def logged_in_user(check_path=True):
    """Get the logged in user

    Args:
        check_path (bool): call `simulation_db.user_path` [True]
    Returns:
        str: uid of authenticated user
    """
    u = _get_user()
    if not _is_logged_in():
        raise util.SRException(
            'login',
            None,
            'user not logged in uid={}',
            u,
        )
    assert u, \
        'no user in cookie: state={} method={}'.format(
            cookie.unchecked_get_value(_COOKIE_STATE),
            cookie.unchecked_get_value(_COOKIE_METHOD),
        )
    if check_path:
        simulation_db.user_path(u, check=True)
    return u


def login(module, uid=None, model=None, sim_type=None, display_name=None, is_mock=False, want_redirect=False):
    """Login the user

    Raises an exception if successful, except in the case of methods

    Args:
        module (module): method module
        uid (str): user to login
        model (auth_db.UserDbBase): user to login (overrides uid)
        sim_type (str): app to redirect to
    """
    _validate_method(module, sim_type=sim_type)
    guest_uid = None
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
        login_fail_redirect(sim_type, module, 'deprecated', reload_js=not uid)
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
            _create_roles_for_user(uid, module.AUTH_METHOD)
        if model:
            model.uid = uid
            model.save()
    if display_name:
        complete_registration(_parse_display_name(display_name))
    if is_mock:
        return
    if sim_type:
        if guest_uid and guest_uid != uid:
            simulation_db.move_user_simulations(guest_uid, uid)
        login_success_response(sim_type, want_redirect)
    assert not module.AUTH_METHOD_VISIBLE


def login_fail_redirect(sim_type=None, module=None, reason=None, reload_js=False):
    raise util.SRException(
        'loginFail',
        PKDict(
            method=module.AUTH_METHOD,
            reason=reason,
            reload_js=reload_js,
            sim_type=sim_type,
        ),
        'login failed: reason={} method={}',
        reason,
        module.AUTH_METHOD,
    )


def login_success_response(sim_type, want_redirect=False):
    r = None
    if (
        cookie.get_value(_COOKIE_STATE) == _STATE_COMPLETE_REGISTRATION
        and cookie.get_value(_COOKIE_METHOD) == METHOD_GUEST
    ):
        complete_registration()
    if want_redirect:
        r = 'completeRegistration' if (
            cookie.get_value(_COOKIE_STATE) == _STATE_COMPLETE_REGISTRATION
        ) else None
        raise sirepo.util.Redirect(sirepo.uri.local_route(sim_type, route_name=r))
    raise sirepo.util.Response(
        response=http_reply.gen_json_ok(PKDict(authState=_auth_state())),
    )


def need_complete_registration(model):
    """Does unauthenticated user need to complete registration?

    If the current method is deprecated, then we will end up asking
    the user for a name again, but that's ok.

    Does not work for guest (which don't have their own models anyway).

    Args:
        model (auth_db.UserDbBase): unauthenticated user record
    Returns:
        bool: True if user will be redirected to needCompleteRegistration
    """
    if not model.uid:
        return True
    return not auth_db.UserRegistration.search_by(uid=model.uid).display_name


def process_request(unit_test=None):
    cookie.process_header(unit_test)
    _set_log_user()


def require_auth_basic():
    m = _METHOD_MODULES['basic']
    _validate_method(m)
    uid = m.require_user()
    if not uid:
        raise sirepo.util.Response(
            sirepo.util.flask_app().response_class(
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="*"'},
            ),
        )
    cookie.set_sentinel()
    login(m, uid=uid)


def require_sim_type(sim_type):
    if sim_type not in sirepo.feature_config.cfg().proprietary_sim_types:
        # only check role for proprietary_sim_types
        return
    if not _is_logged_in():
        # If a user is not logged in, we allow any sim_type, because
        # the GUI has to be able to get access to certain APIs before
        # logging in.
        return
    check_user_has_role(role_for_sim_type(sim_type))


def check_user_has_role(role, raise_forbidden=True):
    u = logged_in_user()
    if auth_db.UserRole.has_role(u, role):
        return True
    if raise_forbidden:
        util.raise_forbidden('uid={} role={} not found'.format(u, role))
    return False


def require_user():
    e = None
    m = cookie.unchecked_get_value(_COOKIE_METHOD)
    p = None
    r = 'login'
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    u = _get_user()
    if s is None:
        e = 'no user in cookie'
    elif s == _STATE_LOGGED_IN:
        if m in cfg.methods:
            f = getattr(_METHOD_MODULES[m], 'validate_login', None)
            if f:
                pkdc('validate_login method={}', m)
                f()
            return
        if m in cfg.deprecated_methods:
            e = 'deprecated'
        else:
            e = 'invalid'
            reset_state()
            p = PKDict(reload_js=True)
        e = 'auth_method={} is {}, forcing login: uid='.format(m, e, u)
    elif s == _STATE_LOGGED_OUT:
        e = 'logged out uid={}'.format(u)
        if m in cfg.deprecated_methods:
            # Force login to this specific method so we can migrate to valid method
            r = 'loginWith'
            p = PKDict({':method': m})
            e = 'forced {}={} uid={}'.format(m, r, p)
    elif s == _STATE_COMPLETE_REGISTRATION:
        if m == METHOD_GUEST:
            pkdc('guest completeRegistration={}', u)
            complete_registration()
            return
        r = 'completeRegistration'
        e = 'uid={} needs to complete registration'.format(u)
    else:
        cookie.reset_state('uid={} state={} invalid, cannot continue'.format(s, u))
        p = PKDict(reload_js=True)
        e = 'invalid cookie state={} uid={}'.format(s, u)
    pkdc('SRException uid={} route={} params={} method={} error={}', u, r, p, m, e)
    raise util.SRException(r, p, 'user not logged in: {}', e)


def reset_state():
    cookie.unchecked_remove(_COOKIE_USER)
    cookie.unchecked_remove(_COOKIE_METHOD)
    cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
    _set_log_user()


def role_for_sim_type(sim_type):
    return 'sim_type_' + sim_type


def set_user_for_utils(uid=None):
    """A mock user for utilities"""
    cookie.set_cookie_for_utils()
    import sirepo.auth.guest
    if uid:
        _login_user(sirepo.auth.guest, uid)
    else:
        login(sirepo.auth.guest, is_mock=True)


@contextlib.contextmanager
def set_user(uid):
    """Set the user (uid) for the context"""
    assert not util.flask_app(), \
        'Flask sets the user on the request'
    try:
        set_user_for_utils(uid=uid)
        yield
    finally:
        reset_state()


def user_dir_not_found(user_dir, uid):
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
    raise util.Redirect(
        sirepo.uri.ROOT,
        'simulation_db dir={} not found, deleted uid={}',
        user_dir,
        uid,
    )


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
            pkdlog(
                'possibly misconfigured server: invalid cookie_method={}, clearing values={}',
                m,
                values,
            )
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


def _auth_state():
    s = cookie.unchecked_get_value(_COOKIE_STATE)
    v = pkcollections.Dict(
        avatarUrl=None,
        displayName=None,
        guestIsOnlyMethod=not non_guest_methods,
        isGuestUser=False,
        isLoggedIn=_is_logged_in(s),
        isLoginExpired=False,
        jobRunModeMap=simulation_db.JOB_RUN_MODE_MAP,
        method=cookie.unchecked_get_value(_COOKIE_METHOD),
        needCompleteRegistration=s == _STATE_COMPLETE_REGISTRATION,
        roles=[],
        userName=None,
        visibleMethods=visible_methods,
    )
    if 'sbatch' in v.jobRunModeMap:
        v.sbatchQueueMaxes=job.NERSC_QUEUE_MAX
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
        v.roles = auth_db.UserRole.search_all_for_column('role', uid=u)
        _method_auth_state(v, u)
    if pkconfig.channel_in('dev'):
        # useful for testing/debugging
        v.uid = u
    pkdc('state={}', v)
    return v


def _create_roles_for_user(uid, method):
    if not (pkconfig.channel_in('dev') and method == METHOD_GUEST):
        return

    auth_db.UserRole.add_roles(uid, get_all_roles())


def _get_user():
    return cookie.unchecked_get_value(_COOKIE_USER)


def _init():
    global cfg

    cfg = pkconfig.init(
        methods=((METHOD_GUEST,), set, 'for logging in'),
        deprecated_methods=(set(), set, 'for migrating to methods'),
        logged_in_user=(None, str, 'Only for sirepo.job_supervisor'),
    )
    if not cfg.logged_in_user:
        return
    global logged_in_user, user_dir_not_found

    def logged_in_user():
        return cfg.logged_in_user

    def user_dir_not_found(d, u):
        # can't raise in a lambda so do something like this
        raise AssertionError('user_dir={} not found'.format(d))

    cfg.deprecated_methods = set()
    cfg.methods = set((METHOD_GUEST,))


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


def _parse_display_name(value):
    res = value.strip()
    assert len(res), \
        'invalid post data: displayName={}'.format(value)
    return res


def _set_log_user():
    a = sirepo.util.flask_app()
    if not a or not a.sirepo_uwsgi:
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
    a.sirepo_uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, u)


def _validate_method(module, sim_type=None):
    if module.AUTH_METHOD in valid_methods:
        return None
    pkdlog('invalid auth method={}'.format(module.AUTH_METHOD))
    login_fail_redirect(sim_type, module, 'invalid-method', reload_js=True)


_init()
