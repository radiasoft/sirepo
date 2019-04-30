# -*- coding: utf-8 -*-
u"""

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import base64
import os


def gen_private_key():
    """Generate 32 byte random private key"""
    import base64
    import os

    return base64.urlsafe_b64encode(os.urandom(32))
