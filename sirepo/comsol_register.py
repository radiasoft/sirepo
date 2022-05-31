# -*- coding: utf-8 -*-
u"""COMSOL registration routes.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import http_reply
from sirepo import smtp
import sirepo.request

cfg = None


class Request(sirepo.request.Base):
    @api_perm.allow_visitor
    def api_comsol(self):
        return http_reply.gen_redirect(
            'https://www.radiasoft.net/services/comsol-certified-consulting/',
        )

    @api_perm.allow_visitor
    def api_comsolRegister(self):
        import sirepo.util
    
        req = self.parse_json()
        smtp.send(
            recipient=cfg.mail_recipient_email,
        subject='Sirepo / COMSOL Registration',
        body=u'''
Request for access to Sirepo / COMSOL.

Name: {}
Email: {}
'''.format(req.name, req.email),
        )
        return http_reply.gen_json_ok()


def init_apis(*args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        mail_recipient_email=pkconfig.Required(str, 'Email to receive registration messages'),
    )
