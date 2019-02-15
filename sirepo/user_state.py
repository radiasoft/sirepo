# -*- coding: utf-8 -*-
u"""User cookie state

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
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
import flask

#: what routeName to return in the event user is logged out in require_user
LOGGED_OUT_ROUTE_NAME = 'loggedOut'

#: login_state values in cookie
_ANONYMOUS = 'a'
_LOGGED_IN = 'li'
_LOGGED_OUT = 'lo'

#: used in query (process_logout) and map for SIREPO.userState
_ANONYMOUS_SESSION = 'anonymous'

#: map so SIREPO.userState in user-state.js
_LOGIN_SESSION_MAP = pkcollections.Dict({
    _ANONYMOUS: _ANONYMOUS_SESSION,
    _LOGGED_IN: 'logged_in',
    _LOGGED_OUT: 'logged_out',
})

#: key for login state
_COOKIE_SESSION = 'sros'

#: formerly used in the cookie but no longer so is removed below
_REMOVED_COOKIE_NAME = 'sron'

#: registered module
login_module = None


def all_uids():
    if login_module:
        return user_db.all_uids(login_module.UserModel)
    return []


@api_perm.allow_visitor
def api_logout(simulation_type):
    return process_logout(simulation_type)


@api_perm.allow_visitor
def api_userState():
    v = pkcollections.Dict(
        # means "no auth method" (is_logged_out is unused when user_state None)
        is_logged_out=False,
        user_state=None,
    )
    if login_module:
        s = cookie.unchecked_get_value(_COOKIE_SESSION, _ANONYMOUS)
        v.user_state = pkcollections.Dict(
            authMethod=login_module.AUTH_METHOD,
            displayName=None,
            loginSession=_LOGIN_SESSION_MAP[s],
            userName=None,
        )
        if pkconfig.channel_in('dev'):
            v.user_state.uid  = cookie.unchecked_get_user()
        if s == _LOGGED_IN:
            u = login_module.UserModel.search_by(uid=cookie.get_user())
            if u:
                v.user_state.update(
                    displayName=u.display_name,
                    userName=u.user_name,
                )
        v.is_logged_out = s == _LOGGED_OUT
    return http_reply.render_static('user-state', 'js', v)


def init_apis(app):
    from sirepo import uri_router

    uri_router.register_api_module()


def init_beaker_compat():
    from sirepo import beaker_compat

    beaker_compat.oauth_hook = _beaker_compat_map_keys


def is_anonymous_session():
    return cookie.unchecked_get_value(_COOKIE_SESSION, _ANONYMOUS) == _ANONYMOUS


def is_logged_in():
    return cookie.unchecked_get_value(_COOKIE_SESSION) == _LOGGED_IN


def login_as_user(user):
    user.login(is_anonymous_session())
    _update_session(_LOGGED_IN)


def logout_as_anonymous():
    cookie.clear_user()
    _update_session(_ANONYMOUS)


def logout_as_user():
    _update_session(_LOGGED_OUT)


def process_logout(simulation_type):
    """Set the current user as logged out. If the 'anonymous' query flag is set,
    clear the user and change to an anonymous session.
    """
    if cookie.has_user_value() and not is_anonymous_session():
        if login_module.ALLOW_ANONYMOUS_SESSION \
           and flask.request.args.get(_ANONYMOUS_SESSION, False):
            logout_as_anonymous()
        else:
            logout_as_user()
    return flask.redirect('/{}'.format(simulation_type))


def register_login_module():
    global login_module

    m = pkinspect.caller_module()
    assert not login_module, \
        'login_module already registered: old={} new={}'.format(login_module, m)
    login_module = m


def require_user():
    if login_module:
        # cookie_name is no longer used so clean up
        cookie.unchecked_remove(_REMOVED_COOKIE_NAME)
        if cookie.has_user_value():
            if is_logged_in():
                return login_module.require_user()
            if not is_anonymous_session():
                return (
                    LOGGED_OUT_ROUTE_NAME,
                    'user={} is logged out'.format(cookie.get_user())
                )
            if login_module.ALLOW_ANONYMOUS_SESSION:
                return None
            return (
                LOGGED_OUT_ROUTE_NAME,
                'user={} is anonymous in auth={}'.format(
                    cookie.get_user(),
                    login_module.AUTH_METHOD,
                ),
            )
        elif not login_module.ALLOW_ANONYMOUS_SESSION:
            return (
                LOGGED_OUT_ROUTE_NAME,
                'no user in cookie',
            )
    elif cookie.has_user_value():
        return None
    from sirepo import simulation_db
    simulation_db.user_create()
    return None


def _beaker_compat_map_keys(key_map):
    key_map['key']['oauth_login_state'] = _COOKIE_SESSION
    # reverse map of login state values
    key_map['value'] = dict(map(lambda k: (_LOGIN_SESSION_MAP[k], k), _LOGIN_SESSION_MAP))


def _update_session(login_state):
    cookie.set_value(_COOKIE_SESSION, login_state)
