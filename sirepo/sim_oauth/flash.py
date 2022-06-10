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

_SIM_TYPE = 'flash'

class API(sirepo.api.Base):

    @api_perm.require_user
    def api_simOauthFlashAuthorized(self):
        o, _ = sirepo.oauth.check_authorized_callback()
        i = PKDict(o.get(cfg.info_url).json())
#TODO(robnagler) should this not raise forbidden?
        assert i.status == cfg.info_valid_user, \
            f'unexpected status in info={i} expect={cfg.info_valid_user}'
        sirepo.auth_db.UserRole.add_role_or_update_expiration(
            sirepo.auth.logged_in_user(),
            sirepo.auth_role.for_sim_type(_SIM_TYPE),
            expiration=datetime.datetime.fromtimestamp(PKDict(o.token).expires_at),
        )
        raise sirepo.util.Redirect(_SIM_TYPE)


def init_apis():
    global cfg
    cfg = pkconfig.init(
        authorize_url=pkconfig.Required(str, 'url to redirect to for authorization'),
        callback_uri=(None, str, 'Flash callback URI (defaults to api_simOauthFlashAuthorized)'),
        info_valid_user=pkconfig.Required(str, 'valid user status code'),
        info_url=pkconfig.required(str, 'to request user data'),
        key=pkconfig.Required(str, 'OAuth key'),
        scope=('openid', str, 'scope of data to request about user'),
        secret=pkconfig.Required(str, 'OAuth secret'),
        token_endpoint=pkconfig.Required(str, 'url for obtaining access token')
    )
    cfg.callback_api = 'simOauthFlashAuthorized'
