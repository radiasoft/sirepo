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

DEV_SMTP_SERVER = 'dev'

def send(self, recipient, subject, body):
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


cfg = pkconfig.init(
    from_email=('support@sirepo.com', str, 'Email addres of sender'),
    from_name=('Sirepo Support', str, 'Name of email sender'),
    password=pkconfig.Required(str, 'SMTP password'),
    port=(587, int, 'SMTP Port'),
    server=pkconfig.Required(str, 'SMTP TLS server'),
    user=pkconfig.Required(str, 'SMTP user'),
)
