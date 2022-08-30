# -*- coding: utf-8 -*-
"""

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def gen_private_key():
    """Generate 32 byte random private key"""
    import base64
    import os
    from pykern import pkcompat

    return pkcompat.from_bytes(base64.urlsafe_b64encode(os.urandom(32)))
