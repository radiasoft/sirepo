# -*- coding: utf-8 -*-
u"""User cookie state

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkcollections
from pykern import pkinspect
from sirepo import api_perm
from sirepo import cookie
from sirepo import http_reply
import flask

# login_state values
_ANONYMOUS = 'a'
_LOGGED_IN = 'li'
_LOGGED_OUT = 'lo'

_ANONYMOUS_STATE = 'anonymous'
_LOGIN_STATE_MAP = pkcollections.Dict({
    _ANONYMOUS: _ANONYMOUS_STATE,
    _LOGGED_IN: 'logged_in',
    _LOGGED_OUT: 'logged_out',
})

#: cookie keys for user state
_COOKIE_STATE = 'sros'


#: registered module
login_module = None


def all_uids():
    if login_module:
        return user_db.all_uids(login_module.UserModel)
    return []


@api_perm.allow_visitor
def api_userState():
    v = pkcollections.Dict(
        # means "have some type of auth method" and is logged out
        is_logged_out=False,
        user_state=None,
    )
    if login_module:
        s = cookie.get_value(_COOKIE_STATE) or _ANONYMOUS
        v.user_state = pkcollections.Dict(
            authMethod=login_module.AUTH_METHOD,
            displayName=None,
            loginState=_LOGIN_STATE_MAP[s],
            userName=None,
        )
        if s == _LOGGED_IN and cookie.has_user_value():
            u = login_module.UserModel.search_by_uid(cookie.get_user())
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


def is_logged_in():
    return cookie.has_key(_COOKIE_STATE) and cookie.get_value(_COOKIE_STATE) == _LOGGED_IN


def process_logout(simulation_type):
    """Set the current user as logged out. If the 'anonymous' query flag is set,
    clear the user and change to an anonymous session.
    """
    if _cookie_has_user():
        if flask.request.args.get(_ANONYMOUS_STATE, False):
            _update_session(_ANONYMOUS)
            cookie.clear_user()
        else:
            _update_session(_LOGGED_OUT)
    return flask.redirect('/{}'.format(simulation_type))


def register_login_module():
    global login_module

    m = pkinspect.caller_module()
    assert not login_module, \
        'login_module already registered: old={} new={}'.format(login_module, m)
    login_module = m


def set_logged_in():
    _update_session(_LOGGED_IN)


def update_from_cookie():
    if cookie.has_sentinel() and not cookie.has_key(_COOKIE_STATE):
        _update_session(_ANONYMOUS)


def _beaker_compat_map_keys(key_map):
    key_map['key']['oauth_login_state'] = _COOKIE_STATE
    # reverse map of login state values
    key_map['value'] = dict(map(lambda k: (_LOGIN_STATE_MAP[k], k), _LOGIN_STATE_MAP))


def _cookie_has_user():
    return cookie.has_user_value() and cookie.has_key(_COOKIE_STATE) \
        and cookie.get_value(_COOKIE_STATE) != _ANONYMOUS


def _update_session(login_state):
    cookie.set_value(_COOKIE_STATE, login_state)
