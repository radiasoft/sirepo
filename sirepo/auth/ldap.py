"""LDAP authentication support
:copyright: Copyright (c) 2018-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
import ldap
import sirepo.quest

AUTH_METHOD = "ldap"

AUTH_METHOD_VISIBLE = True

_cfg = None

#: module handle
this_module = pkinspect.this_module()

class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    def api_authLdapLogin(self):
        req = self.parse_post()
        c = ldap.initialize(_cfg.ldap_server)
        if(len(req.req_data.username) > 256 or len(req.req_data.password) > 256):
            raise AssertionError("login user/pass greater than 256 chars")
        c.simple_bind_s(self._get_escaped(req.req_data.username), req.req_data.password)
        #TODO(BG): Search auth.db (LDAP email? model?) before registering new user, check with Rob/Evan but likely need to determine model and make None if new user
        self.auth.login(this_module, sim_type=req.type, want_redirect=True)

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
        ldap_server=("ldap://192.168.121.164:389", str, " ldap address:port"),
        base_dn=(",ou=users,dc=example,dc=com", str, "base dn"),
    )
