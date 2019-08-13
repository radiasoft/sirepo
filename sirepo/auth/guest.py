# -*- coding: utf-8 -*-
u"""Guest login

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import cookie
from sirepo import http_reply
from sirepo import srtime
import datetime
import sirepo.template


AUTH_METHOD = auth.METHOD_GUEST

#: User can see it
AUTH_METHOD_VISIBLE = True

#: module handle
this_module = pkinspect.this_module()

#: time to recheck login against db (prefix is "sraz", because github is "srag")
_COOKIE_EXPIRY_TIMESTAMP = 'srazt'

_ONE_DAY = datetime.timedelta(days=1)


@api_perm.require_cookie_sentinel
def api_authGuestLogin(simulation_type):
    """You have to be an anonymous or logged in user at this point"""
    t = sirepo.template.assert_sim_type(simulation_type)
    # if already logged in as guest, just redirect
    if auth.user_if_logged_in(AUTH_METHOD):
        return auth.login_success_redirect(t)
    auth.login(this_module, sim_type=t)
    auth.complete_registration()
    return auth.login_success_redirect(t)


def init_apis(*args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        expiry_days=(None, _cfg_login_days, 'when auth login expires'),
    )


def validate_login():
    """If expiry is configured, check timestamp

    Returns:
        object: if valid, None, otherwise flask.Response.
    """
    if not cfg.expiry_days:
        return None
    n = int(srtime.utc_now_as_float())
    t = int(cookie.unchecked_get_value(_COOKIE_EXPIRY_TIMESTAMP, 0))
    if n <= t:
        # cached timestamp less than expiry
        return None
    # db expiry at most one day from now so we can change expiry_days
    # and (in any event) ensure expiry is checked once a day. This
    # would also allow us to extend the expired period in the db.
    u = auth.logged_in_user()
    r = auth.user_registration(u)
    t = r.created + cfg.expiry_days
    n = srtime.utc_now()
    if n <= t:
        t2 = n + _ONE_DAY
        if t2 < t:
            t = t2
        t -= datetime.datetime.utcfromtimestamp(0)
        cookie.set_value(_COOKIE_EXPIRY_TIMESTAMP, int(t.total_seconds()))
        return None
    pkdlog('expired uid={}, timestamp={} now={}', u, t, n)
    return http_reply.gen_sr_exception(
        'loginFail',
        {
            ':method': 'guest',
            ':reason': 'guest-expired',
        },
    )


def _cfg_login_days(value):
    value = int(value)
    if value == 0:
        return None
    assert value >= 1
    return datetime.timedelta(days=value)
