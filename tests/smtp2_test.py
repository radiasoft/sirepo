# -*- coding: utf-8 -*-
u"""conditionally test smtp

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import os
import pytest


pytestmark = pytest.mark.skipif(not os.environ.get('SIREPO_TESTS_SMTP_EMAIL'), reason='$SIREPO_TESTS_SMTP_EMAIL not set')


def test_send_directly():
    import pykern.pkconfig
    from pykern.pkcollections import PKDict

    pykern.pkconfig.reset_state_for_testing(
        PKDict(
            SIREPO_SMTP_SEND_DIRECTLY='0',
        ),
    )
    import sirepo.smtp
    import sirepo.util

    assert sirepo.smtp.cfg.server != sirepo.smtp._DEV_SMTP_SERVER
    sirepo.smtp.send(
        os.environ.get('SIREPO_TESTS_SMTP_EMAIL'),
        f'sirepo.smtp2_test {sirepo.util.random_base62(5)}',
        'This is a message from sirepo/tests/smtp2_test.py\n',
    )
