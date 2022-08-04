# -*- coding: utf-8 -*-
"""COMSOL registration routes.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import http_reply
from sirepo import smtp
import sirepo.api

cfg = None


class API(sirepo.api.Base):
    @sirepo.api.Spec("allow_visitor")
    def api_comsol(self):
        return self.reply_redirect(
            "https://www.radiasoft.net/services/comsol-certified-consulting/",
        )

    @sirepo.api.Spec("allow_visitor", name="UserDisplayName", email="Email")
    def api_comsolRegister(self):
        req = self.parse_json()
        smtp.send(
            recipient=cfg.mail_recipient_email,
            subject="Sirepo / COMSOL Registration",
            body="""
Request for access to Sirepo / COMSOL.

Name: {}
Email: {}
""".format(
                req.name, req.email
            ),
        )
        return self.reply_ok()


def init_apis(*args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        mail_recipient_email=pkconfig.Required(
            str, "Email to receive registration messages"
        ),
    )
