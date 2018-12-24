# -*- coding: utf-8 -*-
u"""User cookie state

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo import cookie
from pykern import pkcollections

# login_state values
_ANONYMOUS = 'a'
_LOGGED_IN = 'li'
_LOGGED_OUT = 'lo'

_ANONYMOUS_STATE = 'anonymous'
_LOGIN_STATE_MAP = {
    _ANONYMOUS: _ANONYMOUS_STATE,
    _LOGGED_IN: 'logged_in',
    _LOGGED_OUT: 'logged_out',
}

# cookie keys for user state
_COOKIE_NAME = 'sron'
_COOKIE_STATE = 'sros'


def init_beaker_compat():
    from sirepo import beaker_compat
    beaker_compat.oauth_hook = _beaker_compat_map_keys


def set_anonymous():
    _update_session(_ANONYMOUS)
    cookie.clear_user()


def set_default_state(logged_out_as_anonymous=False):
    if not cookie.has_sentinel():
        return None
    if not cookie.has_key(_COOKIE_STATE):
        _update_session(_ANONYMOUS)
    elif logged_out_as_anonymous and cookie.get_value(_COOKIE_STATE) == _LOGGED_OUT:
        _update_session(_ANONYMOUS)
    return pkcollections.Dict(
        login_state=_LOGIN_STATE_MAP.get(cookie.get_value(_COOKIE_STATE), _ANONYMOUS_STATE),
        user_name=cookie.get_value(_COOKIE_NAME),
    )


def set_logged_in(user_name):
    _update_session(_LOGGED_IN, user_name)


def set_logged_out():
    _update_session(_LOGGED_OUT)


def _beaker_compat_map_keys(key_map):
    key_map['key']['oauth_login_state'] = _COOKIE_STATE
    key_map['key']['oauth_user_name'] = _COOKIE_NAME
    # reverse map of login state values
    key_map['value'] = dict(map(lambda k: (_LOGIN_STATE_MAP[k], k), _LOGIN_STATE_MAP))


def _update_session(login_state, user_name=''):
    cookie.set_value(_COOKIE_STATE, login_state)
    cookie.set_value(_COOKIE_NAME, user_name)
