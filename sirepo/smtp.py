# -*- coding: utf-8 -*-
u"""SMTP connection to send emails

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp, pkdlog
from pykern import pkconfig
from pykern.pkcollections import PKDict
import email
import smtplib

_DEV_SMTP_SERVER = 'dev'
_SEND = None
cfg = None


def send(recipient, subject, body):
    if cfg.server == _DEV_SMTP_SERVER:
        pkdlog('DEV configuration so not sending to {}', recipient)
        return False
    m = email.message.EmailMessage()
    m['From'] = f'{cfg.from_name} <{cfg.from_email}>'
    m['To'] = recipient
    m['Subject'] = subject
    m.set_content(body)
    _SEND(m)
    return True


def _mx(msg):
    import dns.resolver

    h = msg['To'].split('@')[1]
    try:
        for x in sorted(
            dns.resolver.resolve(h, 'MX'),
            key=lambda x: x.preference,
        ):
            yield str(x.exchange)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        yield h


def _send_directly(msg):
    for h in _mx(msg):
        # Port 465 is not an official IETF port for SMTPS and has been
        # reassigned so always try port 25 with starttls. stmplib will try
        # 465 if it can import ssl even if the remote server doesn't support it.
        with smtplib.SMTP(h, 25) as s:
            try:
                s.starttls()
            except smtplib.SMTPNotSupportedError:
                pass
            s.ehlo()
            s.send_message(msg)


def _send_with_auth(msg):
    with smtplib.SMTP(cfg.server, cfg.port) as s:
        s.starttls()
        s.ehlo()
        s.login(cfg.user, cfg.password)
        s.send_message(msg)


def _init():
    global cfg, _SEND
    if cfg:
        return
    cfg = pkconfig.init(
        from_email=('support@sirepo.com', str, 'Email address of sender'),
        from_name=('Sirepo Support', str, 'Name of email sender'),
        password=(None, str, 'SMTP password'),
        port=(587, int, 'SMTP Port'),
        send_directly=(False, bool, 'Send directly to the server in the recipient'),
        server=(None, str, 'SMTP TLS server'),
        user=(None, str, 'SMTP user'),
    )
    if cfg.send_directly:
        cfg.server = 'not ' + _DEV_SMTP_SERVER
        _SEND = _send_directly
        return
    _SEND = _send_with_auth
    if pkconfig.channel_in('dev'):
        if cfg.server is None:
            cfg.server = _DEV_SMTP_SERVER
        return
    if cfg.server is None or cfg.user is None or cfg.password is None:
        pkconfig.raise_error(
            f'server={cfg.server}, user={cfg.user}, and password={cfg.password} must be defined',
        )

_init()
