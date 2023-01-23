"""LDAP authentication support
:copyright: Copyright (c) 2018-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
import datetime
import ldap
import sirepo.srtime
import sirepo.quest
import sirepo.util

AUTH_METHOD = "ldap"

AUTH_METHOD_VISIBLE = True

#: Well known alias for auth
UserModel = "AuthEmailUser"

_cfg = None

#: module handle
this_module = pkinspect.this_module()

#: how long before token expires
_EXPIRES_MINUTES = 8 * 60

#: for adding to now
_EXPIRES_DELTA = datetime.timedelta(minutes=_EXPIRES_MINUTES)

class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    def api_authLdapLogin(self):

        req = self.parse_post()
        # TODO(BG): See 'email' as temp often, should be single char or not temp?
        email = req.req_data.username
        c = ldap.initialize(_cfg.ldap_server)
        if(len(email) > 256 or len(req.req_data.password) > 256):
            raise AssertionError("login user/pass greater than 256 chars")
        c.simple_bind(self._get_escaped(email), req.req_data.password)
        # TODO(BG): Test ldap.result() as proper authentication confirmation, currently a quick fix
        try:
            c.result()
        except:
            # TODO(BG): Handle wrong user/pass case, enable button after failed login, display message?
            pkdp("Invalid User/Pass")
        else:
            # TODO(BG): Can move code to an ldap.py auth_db method (similar to auth_db/email.py), see if needed
            m = self.auth_db.model(UserModel)
            u = m.unchecked_search_by(unverified_email=email)
            if not u:
                u = m.new(unverified_email=email)
                # TODO(BG): Make user_name the ldap email or Full Name from registration? Unsure if unverified email works as final email column 
                u.user_name = u.unverified_email
                u.token = sirepo.util.create_token(email)
                # TODO(BG): Expires likely irrelevant for LDAP
                u.expires = sirepo.srtime.utc_now() + _EXPIRES_DELTA
                u.save()
            # TODO(BG): Login by model currently, should login by uid? (mentioned on github)
            self.auth.login(this_module, sim_type=req.type, model=u, want_redirect=True)

        return PKDict()

    # escapes special chars for ldap validity
    def _get_escaped(self, username):
        e = ["+", ";", ",", "\\", '"', "<", ">", "#"]
        v = ""
        for c in username:
            if c in e:
                v += "\\" + c
            else:
                v += c
        return "mail=" + v + _cfg.base_dn


def init_apis(*args, **kwargs):
    global _cfg
    pkdp("calling to _cfg")
    _cfg = pkconfig.init(
        ldap_server=("ldap://10.10.10.10:389", str, " ldap address:port"),
        base_dn=(",ou=users,dc=example,dc=com", str, "base dn"),
    )
