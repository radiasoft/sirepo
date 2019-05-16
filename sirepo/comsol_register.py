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
from sirepo import http_request
from sirepo import uri_router
import flask
import flask_mail


@api_perm.allow_visitor
def api_comsol():
    return server.javascript_redirect('/old#/comsol')


@api_perm.allow_visitor
def api_comsolRegister():
    req = http_request.parse_json()
    msg = flask_mail.Message(
        subject='Sirepo / COMSOL Registration',
        sender=cfg.mail_support_email,
        recipients=[cfg.mail_recipient_email],
        body=u'''
Request for access to Sirepo / COMSOL.

Name: {}
Email: {}
'''.format(req.name, req.email),
    )
    _mail.send(msg)
    return http_reply.gen_json_ok()


def init_apis(app, *args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        mail_server=(None, str, 'Mail server'),
        mail_username=(None, str, 'Mail user name'),
        mail_password=(None, str, 'Mail password'),
        mail_support_email=(None, str, 'Support email address'),
        mail_recipient_email=(None, str, 'Email to receive registration messages'),
    )
    assert cfg.mail_server and cfg.mail_username and cfg.mail_password \
        and cfg.mail_support_email and cfg.mail_recipient_email, \
        'Missing mail config'
    app.config.update(
        MAIL_USE_TLS=True,
        MAIL_PORT=587,
        MAIL_SERVER=cfg.mail_server,
        MAIL_USERNAME=cfg.mail_username,
        MAIL_PASSWORD=cfg.mail_password,
    )
    global _mail
    _mail = flask_mail.Mail(app)
