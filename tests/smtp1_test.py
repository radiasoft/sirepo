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
            SIREPO_SMTP_SEND_DIRECTLY='1',
        ),
    )
    import sirepo.smtp
    import sirepo.util

    sirepo.smtp.send(
        os.environ.get('SIREPO_TESTS_SMTP_EMAIL'),
        f'sirepo.smtp1_test {sirepo.util.random_base62(5)}',
        'This is a message from sirepo/tests/smtp1_test.py\n',
    )
