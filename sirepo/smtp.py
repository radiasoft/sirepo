# -*- coding: utf-8 -*-
u"""SMTP connection to send emails

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
import email
import smtplib

_DEV_SMTP_SERVER = 'dev'

def send(recipient, subject, body):
    if cfg.server == _DEV_SMTP_SERVER:
        return False
    m = email.message.EmailMessage()
    m['From'] = f'{cfg.from_name} <{cfg.from_email}>'
    m['To'] = recipient
    m['Subject'] = subject
    m.set_content(body)
    with smtplib.SMTP(cfg.server, cfg.port) as s:
        s.starttls()
        s.ehlo()
        s.login(cfg.user, cfg.password)
        s.send_message(m)
    return True


cfg = pkconfig.init(
    from_email=('support@sirepo.com', str, 'Email address of sender'),
    from_name=('Sirepo Support', str, 'Name of email sender'),
    password=pkconfig.RequiredUnlessDev('n/a', str, 'SMTP password'),
    port=(587, int, 'SMTP Port'),
    server=pkconfig.RequiredUnlessDev(_DEV_SMTP_SERVER, str, 'SMTP TLS server'),
    user=pkconfig.RequiredUnlessDev('n/a', str, 'SMTP user'),
)
