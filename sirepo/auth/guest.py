# -*- coding: utf-8 -*-
"""Guest login

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import datetime
import sirepo.auth
import sirepo.quest
import sirepo.srtime
import sirepo.util


AUTH_METHOD = sirepo.auth.METHOD_GUEST

#: User can see it
AUTH_METHOD_VISIBLE = True

#: module handle
this_module = pkinspect.this_module()

#: time to recheck login against db (prefix is "sraz", because github was "srag")
_COOKIE_EXPIRY_TIMESTAMP = "srazt"

_ONE_DAY = datetime.timedelta(days=1)


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    async def api_authGuestLogin(self, simulation_type):
        """You have to be an anonymous or logged in user at this point"""
        req = self.parse_params(type=simulation_type)
        # if already logged in as guest, just redirect
        if self.auth.user_if_logged_in(AUTH_METHOD):
            self.auth.login_success_response(req.type)
        self.auth.login(this_module, sim_type=req.type)
        raise AssertionError("auth.login returned unexpectedly")


def is_login_expired(qcall, res=None):
    """If expiry is configured, check timestamp

    Args:
        res (hash): If a hash and return is True, will contain (uid, expiry, and now).

    Returns:
        bool: true if login is expired
    """
    if not cfg.expiry_days:
        return False
    n = sirepo.srtime.utc_now_as_int()
    t = int(qcall.cookie.unchecked_get_value(_COOKIE_EXPIRY_TIMESTAMP, 0))
    if n <= t:
        # cached timestamp less than expiry
        return False
    # db expiry at most one day from now so we can change expiry_days
    # and (in any event) ensure expiry is checked once a day. This
    # would also allow us to extend the expired period in the db.
    u = qcall.auth.logged_in_user()
    r = qcall.auth.user_registration(u)
    t = r.created + cfg.expiry_days
    n = sirepo.srtime.utc_now()
    if n > t:
        if res is not None:
            res.update(uid=u, expiry=t, now=n)
        return True
    # set expiry in cookie
    t2 = n + _ONE_DAY
    if t2 < t:
        t = t2
    t -= datetime.datetime.utcfromtimestamp(0)
    qcall.cookie.set_value(_COOKIE_EXPIRY_TIMESTAMP, int(t.total_seconds()))
    return False


def validate_login(qcall):
    """If expiry is configured, check timestamp

    Raises SRException loginFail if expired.
    """
    msg = PKDict()
    if is_login_expired(qcall, msg):
        raise sirepo.util.SRException(
            "loginFail",
            PKDict(method="guest", reason="guest-expired"),
            "expired uid={uid}, expiry={expiry} now={now}",
            **msg
        )


def _cfg_login_days(value):
    value = int(value)
    if value == 0:
        return None
    assert value >= 1
    return datetime.timedelta(days=value)


cfg = pkconfig.init(
    expiry_days=(None, _cfg_login_days, "when auth login expires"),
)
