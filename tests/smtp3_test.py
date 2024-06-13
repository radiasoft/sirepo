"""test smtp logic, not sending

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_msg():
    from pykern.pkcollections import PKDict
    from pykern import pkconfig

    d = "from-domain.com"
    pkconfig.reset_state_for_testing(
        PKDict(
            SIREPO_SMTP_SEND_DIRECTLY="1",
            SIREPO_SMTP_FROM_EMAIL=f"sender@{d}",
        ),
    )

    from sirepo import smtp
    from pykern import pkunit

    m = None

    def _send(value):
        nonlocal m
        m = value

    smtp._SEND = _send
    smtp.send(
        "any-user@recipient-domain.com",
        "any-subject",
        "any-body",
    )
    pkunit.pkre(d, m["Message-Id"])
