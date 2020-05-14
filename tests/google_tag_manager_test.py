# -*- coding: utf-8 -*-
"""Test(s) for static files

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import os

_NO_SUCH_ID = '__NO_SUCH_GOOGLE_TAG_ID__'


def setup_module(module):
    os.environ.update(
        SIREPO_SERVER_GOOGLE_TAG_MANAGER_ID=_NO_SUCH_ID,
    )


def test_injection(fc):
    from pykern import pkcompat, pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    from pykern.pkunit import pkeq, pkok, pkre
    import re

    # test non-static page
    r = fc.get('myapp')
    pkok(
        not re.search(
            r'https://www.googletagmanager.com/gtm.js\?id=',
            pkcompat.from_bytes(r.data)
        ),
        'Unexpected injection of google tag mgr'
    )

    # test successful injection
    r = fc.get('/en/landing.html')
    pkok(
        re.search(_NO_SUCH_ID, pkcompat.from_bytes(r.data)),
        'Missing injection of google tag mgr'
    )

