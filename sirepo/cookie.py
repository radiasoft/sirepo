# -*- coding: utf-8 -*-
u"""User session management via an HTTP cookie

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkcollections
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import util
import base64
import flask
import re
import sirepo.beaker_compat

# Max age in seconds
_COOKIE_MAX_AGE = 10 * 365 * 24 * 3600

#: Identifies if the session has been returned by the client
_SESSION_KEY_COOKIE_SENTINEL = 'srk'

#: Identifies the user in the session
_SESSION_KEY_USER = 'sru'


def clear_user():
    if has_key(_SESSION_KEY_USER):
        remove(_SESSION_KEY_USER)


def get(key):
    return _cookie()[key]


def get_user(checked=True):
    return _cookie().get_user(checked)


def has_key(key):
    return key in _cookie()


def init(logger):
    header = flask.request.environ['HTTP_COOKIE'] if 'HTTP_COOKIE' in flask.request.environ else ''
    _cookie(_Session(header, logger))


def remove(key):
    del _cookie()[key]


def save_to_cookie(response):
    _cookie().save_to_cookie(response)


def set(key, value):
    _cookie()[key] = value


def set_user(uid):
    _cookie().set_user(uid)


def init_mock(uid):
    """A mock session for pkcli"""
    res = _Session('', None)
    res[_SESSION_KEY_USER] = uid
    res[_SESSION_KEY_COOKIE_SENTINEL] = 1
    flask.g = pkcollections.Dict({
        'sirepo_cookie': res,
    })


def _cookie(v=None):
    if v is not None:
        flask.g.sirepo_cookie = v
    return flask.g.sirepo_cookie


class _Session(dict):

    def __init__(self, header, logger):
        self.logger = logger
        self._from_cookie_header(header)
        self._log_user()

    def get_user(self, checked=True):
        if not self.get(_SESSION_KEY_COOKIE_SENTINEL):
            util.raise_forbidden('Missing session, cookies may be disabled')
        return self[_SESSION_KEY_USER] if checked else self.get(_SESSION_KEY_USER)

    def save_to_cookie(self, response):
        if 200 <= response.status_code < 400:
            self[_SESSION_KEY_COOKIE_SENTINEL] = 1
            #TODO(pjm): don't set if it already matches
            response.set_cookie(cfg.key, self._to_cookie_value(), max_age=_COOKIE_MAX_AGE)

    def set_user(self, uid):
        assert uid
        self[_SESSION_KEY_USER] = uid
        self._log_user()

    def _from_cookie_header(self, header):
        match = re.search('{}=([^;]+)'.format(cfg.key), header)
        if match:
            values = base64.urlsafe_b64decode(match.group(1))
            #TODO(pjm): decrypt
            for pair in values.split(' '):
                match = re.search(r'^([^=]+)=(.*)', pair)
                assert match
                k, v = match.groups(1)
                self[k] = v
        if not self.get(_SESSION_KEY_COOKIE_SENTINEL):
            sirepo.beaker_compat.update_session_from_cookie_header(header)


    def _log_user(self):
        if self.logger:
            self.logger.set_log_user(self.get(_SESSION_KEY_USER))

    def _to_cookie_value(self):
        #TODO(pjm): encrypt
        return base64.urlsafe_b64encode(' '.join(map(lambda k: '{}={}'.format(k, self[k]), self.keys())))


cfg = pkconfig.init(
    key=('sirepo_' + pkconfig.cfg.channel, str, 'Name of the cookie key used to save the session under'),
    secret=(None, str, 'Cookie encryption secret'),
)
