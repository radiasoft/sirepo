"""LDAP login
:copyright: Copyright (c) 2018-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
import ldap
import sirepo.quest

AUTH_METHOD = "ldap"

AUTH_METHOD_VISIBLE = True

_cfg = None

class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    def api_authLdapAuthorized(self):

        # TODO(BG) Move req data to cfg?
        req = self.parse_post(type=False)

        c = ldap.initialize(_cfg.ldap_server)
        
        #if(len(req.req_data.username) > 256 | len(req.req_data.password > 256)):
            #raise Exception("login user/pass greater than 256 chars")
        
        c.simple_bind_s(
            self._get_escaped(req.req_data.username), req.req_data.password
        )

        return PKDict()
    
    # escapes special chars for ldap validity
    def _get_escaped(self, username):
        #TODO(BG) Move e to ldap?
        e = ['+', ';', ',', '\\', '\"', '<', '>', '#']
        v = ""
            
        for c in username:
            if(c in e):
                v += '\\' + c
            else:
                v += c
        return "mail=" + v + _cfg.base_dn
    
def init_apis(*args, **kwargs):
    global _cfg
    
    pkdp("calling to _cfg")
    _cfg = pkconfig.init(
        ldap_server=("ldap://192.168.121.164:389", str, " ldap address:port"),
        base_dn=(",ou=users,dc=example,dc=com", str, "base dn")
    )