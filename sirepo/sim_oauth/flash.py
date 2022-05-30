# -*- coding: utf-8 -*-
u"""Oauth API's for flash sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import api_perm
import datetime
import sirepo.api
import sirepo.auth
import sirepo.auth_db
import sirepo.auth_role
import sirepo.oauth
import sirepo.srtime
import sirepo.util

cfg = None

class API(sirepo.api.Base):
    @api_perm.require_user
    def api_simOauthFlashAuthorized(self):
        oc, _ = sirepo.oauth.check_authorized_callback()
        r = PKDict(oc.token)
        i = PKDict(oc.get('https://flash.rochester.edu/id/userinfo').json())
        assert i.status == 'G', \
            f'unexpected status in userinfo={i}'
        sirepo.auth_db.UserRole.add_role_or_update_expiration(
            sirepo.auth.logged_in_user(),
            sirepo.auth_role.for_sim_type('flash'),
            expiration=datetime.datetime.fromtimestamp(r.expires_at),
        )
        raise sirepo.util.Redirect('flash')


def init_apis():
    global cfg
    cfg = pkconfig.init(
        authorize_url=('https://flash.rochester.edu/id/oauth2/auth', str, 'url to redirect to for authorization'),
        callback_uri=(None, str, 'Flash callback URI (defaults to api_simOauthFlashAuthorized)'),
        key=pkconfig.Required(str, 'OAuth key'),
        scope=('openid', str, 'scope of data to request about user'),
        secret=pkconfig.Required(str, 'OAuth secret'),
        token_endpoint=('https://flash.rochester.edu/id/oauth2/token', str, 'url for obtaining access token')
    )
    cfg.callback_api = 'simOauthFlashAuthorized'
