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
import flask
import importlib


#: what routeName to return in the event user is logged out in require_user
LOGGED_OUT_ROUTE_NAME = 'loggedOut'

_AUTH_METHOD_ANONYMOUS_COOKIE_VALUE = 'a'
_AUTH_METHOD_ANONYMOUS_MODULE_NAME = 'anonymous'

#: login_state values in cookie
_ANONYMOUS_DEPRECATED = 'a'
_LOGGED_IN = 'li'
_LOGGED_OUT = 'lo'

#: used in query of api_logout to indicate an anonymous session
_ANONYMOUS_LOGIN_QUERY = 'anonymous'

#: key for logged in
_COOKIE_LOGGED_IN = 'srali'

#: key for auth method for login state
_COOKIE_AUTH_METHOD = 'sralm'

#: key for need user name
_COOKIE_COMPLETE_REGISTRATION = 'sracr'

#: oauth._COOKIE_STATE migrated to  _COOKIE_AUTH_METHOD and _COOKIE_LOGIN_SESSION
_COOKIE_SESSION_DEPRECATED = 'sros'

#: formerly used in the cookie but no longer so is removed below
_REMOVED_COOKIE_NAME = 'sron'

#: registered module
_METHOD_MODULES = pkcollections.Dict()


@api_perm.require_user
def api_authDisplayName():
    data = http_request.parse_json(assert_sim_type=False)
    dn = _parse_display_name(data)
    uid = cookie.get_user()
    assert is_logged_in(), \
        'user is not logged in, uid={}'.format(uid)
    with user_db.thread_lock:
        user = EmailAuth.search_by(uid=uid)
        user.display_name = dn
        user.save()
    return http_reply.gen_json_ok()


@api_perm.allow_visitor
def api_logout(simulation_type):
    """Set the current user as logged out. If the 'anonymous' query flag is set,
    clear the user and change to an anonymous session.
    """
    migrate_cookie_keys()
    if cookie.has_user_value() and not is_anonymous_session():
        if login_module.ALLOW_ANONYMOUS_SESSION \
           and flask.request.args.get(_ANONYMOUS_LOGIN_QUERY, False):
            logout_as_anonymous()
        else:
            logout_as_user()
    return flask.redirect('/{}'.format(simulation_type))


@api_perm.allow_visitor
def api_userState():
    migrate_cookie_keys()
    a = cookie.unchecked_get_value(_COOKIE_AUTH_METHOD, _AUTH_METHOD_ANONYMOUS_COOKIE_VALUE)
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
            u = login_module.UserModel.search_by(uid=cookie.get_user())
            if u:
                v.user_state.update(
                    displayName=u.display_name,
                    userName=u.user_name,
                )
    return http_reply.render_static('user-state', 'js', v)


def init_apis(app):
    from sirepo import uri_router

    assert not _METHOD_MODULES
    p = pkinspect.this_module().__name__
    for m in cfg.methods:
        x = importlib.import_module(pkinspect.module_name_join(p, m))
        _METHOD_CLASS[m] = _METHOD_MODULES[m].init_auth_method(x)
    uri_router.register_api_module()


def init_beaker_compat():
    from sirepo import beaker_compat

    beaker_compat.oauth_hook = _beaker_compat_map_keys


def is_anonymous_session():
    migrate_cookie_keys()
    return cookie.get_value(_COOKIE_AUTH_METHOD) == _AUTH_METHOD_ANONYMOUS_COOKIE_VALUE


def login_as_user(user, module):
    migrate_cookie_keys()
    user.login(is_anonymous_session())
    _update_session(_LOGGED_IN, module.AUTH_METHOD_COOKIE_VALUE)


def logout_as_anonymous():
    migrate_cookie_keys()
    cookie.clear_user()
    _update_session(_LOGGED_OUT, _AUTH_METHOD_ANONYMOUS_COOKIE_VALUE)


def logout_as_user(module):
    migrate_cookie_keys()
    _update_session(_LOGGED_OUT, module.AUTH_METHOD_COOKIE_VALUE)


def migrate_cookie_keys():
    if cookie.has_key(_COOKIE_AUTH_METHOD):
        return
    # cookie_name is no longer used so clean up
    cookie.unchecked_remove(_REMOVED_COOKIE_NAME)
    if not cookie.has_sentinel():
        # not initialized
        return
    if not cookie.has_key(_COOKIE_SESSION_DEPRECATED):
        _update_session(
            _LOGGED_IN if cookie.has_user_value() else _LOGGED_OUT,
            _AUTH_METHOD_ANONYMOUS_COOKIE_VALUE,
        )
        return
    os = cookie.unchecked_remove(_COOKIE_SESSION_DEPRECATED)
    if os == _AUTH_METHOD_ANONYMOUS_MODULE_NAME:
        _update_session(_LOGGED_OUT, _AUTH_METHOD_ANONYMOUS_COOKIE_VALUE)

eoauth_anonymous
anonymous login module needs to be there.



    if no cookie whatsoever


set auth method and
    to do


def require_user():
    migrate_cookie_keys()
    if cookie.unchecked_get_value(_COOKIE_LOGIN_SESSION) == _LOGGED_IN:
        a = cookie.get_value(_COOKIE_AUTH_METHOD)
        if a not in valid_methods:
            return (
                LOGGED_OUT_ROUTE_NAME,
                'auth_method={} invalid, force login to valid method: uid='.format(
                    a,
                    cookie.get_user(),
                ),
            )
        return None
    u = unchecked_get_user()
    return (
        LOGGED_OUT_ROUTE_NAME,
        'logged out user={}'.format(u) if u else 'no user in cookie',
    )


def _beaker_compat_map_keys(key_map):
_LOGIN_SESSION_MAP = pkcollections.Dict({
    _ANONYMOUS_DEPRECATED: _AUTH_METHOD_ANONYMOUS_MODULE_NAME,
    _LOGGED_IN: 'logged_in',
    _LOGGED_OUT: 'logged_out',
})

    key_map['key']['oauth_login_state'] = _COOKIE_SESSION_DEPRECATED
    # reverse map of login state values
    key_map['value'] = {v: k for k, v in .iteritems()}
    dict(map(lambda k: (_LOGIN_SESSION_MAP[k], k), _LOGIN_SESSION_MAP))


def _update_session(login_state, auth_method):
    cookie.set_value(_COOKIE_LOGIN_SESSION, login_state)
    cookie.set_value(_COOKIE_AUTH_METHOD, auth_method)


cfg = pkconfig.init(
    methods=(('guest',), tuple, 'From email address'),
)
