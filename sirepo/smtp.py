"""SMTP connection to send emails

:copyright: Copyright (c) 2018-2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdp, pkdlog
from pykern import pkconfig
from pykern.pkcollections import PKDict
import email
import email.utils
import pyisemail
import smtplib

_DEV_SMTP_SERVER = "dev"
_SEND = None
_FROM_DOMAIN = None
_cfg = None


def send(recipient, subject, body):
    if _cfg.server == _DEV_SMTP_SERVER:
        pkdlog("DEV configuration so not sending to {}", recipient)
        return False
    m = email.message.EmailMessage()
    m["From"] = f"{_cfg.from_name} <{_cfg.from_email}>"
    m["To"] = recipient
    m["Subject"] = subject
    m["Message-Id"] = email.utils.make_msgid(domain=_FROM_DOMAIN)
    m.set_content(body)
    _SEND(m)
    return True


def _cfg_from_email(value):
    if not pyisemail.is_email(value):
        pkconfig.raise_error(f"invalid from_email={value}")
    return value.lower()


def _mx(msg):
    import dns.resolver

    h = msg["To"].split("@")[1]
    try:
        for x in sorted(
            dns.resolver.resolve(h, "MX"),
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


def _send_via_relay_server(msg):
    with smtplib.SMTP(_cfg.server, _cfg.port) as s:
        s.starttls()
        s.ehlo()
        if _cfg.user and _cfg.password:
            s.login(_cfg.user, _cfg.password)
        s.send_message(msg)


def _init():
    global _cfg, _SEND, _FROM_DOMAIN
    if _cfg:
        return
    _cfg = pkconfig.init(
        from_email=("support@sirepo.com", _cfg_from_email, "Email address of sender"),
        from_name=("Sirepo Support", str, "Name of email sender"),
        password=(None, str, "SMTP password"),
        port=(587, int, "SMTP Port"),
        send_directly=(False, bool, "Send directly to the server in the recipient"),
        server=(None, str, "SMTP TLS server"),
        user=(None, str, "SMTP user"),
    )
    _FROM_DOMAIN = _cfg.from_email.split("@")[1]
    if _cfg.send_directly:
        _cfg.server = "not " + _DEV_SMTP_SERVER
        _SEND = _send_directly
        return
    _SEND = _send_via_relay_server
    if pkconfig.in_dev_mode():
        if _cfg.server is None:
            _cfg.server = _DEV_SMTP_SERVER
        return
    if _cfg.server is None:
        pkconfig.raise_error(
            f"server={_cfg.server} must be defined",
        )
    if bool(_cfg.user) != bool(_cfg.password):
        pkconfig.raise_error(
            f"user={_cfg.user} and password={_cfg.password} must be both set or not"
        )


_init()
