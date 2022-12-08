"""LDAP login
:copyright: Copyright (c) 2018-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdlog, pkdp
from pykern.pkcollections import PKDict
import sirepo.quest
import ldap

AUTH_METHOD = "ldap"

#: User can see it
AUTH_METHOD_VISIBLE = True

class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_cookie_sentinel")
    def api_authLdapAuthorized(self):
        """Python-LDAP client authentication
        Bind to server and authenticate
        """
        #Test User Credentials:
        #username: Archimedes of Syracuse
        #password: eureka

        LDAP_SERVER = 'ldap://10.10.10.10:389'
        BASE_DN = 'dc=example,dc=com'
        OBJECT_TO_SEARCH = 'objectClass=inetOrgPerson'
        ATTRIBUTES_TO_SEARCH = ['uid']

        req = self.parse_post(type=False)
        pkdp("req: {}", req.req_data.username)

        #initialize our connect to ldap-server
        connect = ldap.initialize(LDAP_SERVER)

        #bind to server and login
        connect.simple_bind_s(self._get_login(req.req_data.username), req.req_data.password)

        return PKDict()

    def _get_login(self, username):
        return 'cn=' + username + ',ou=users,dc=example,dc=com'
    