# -*- coding: utf-8 -*-
u"""Utilities for requests

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdlog
import werkzeug.exceptions


def raise_not_found(fmt, *args, **kwargs):
    pkdlog(fmt, *args, **kwargs)
    raise werkzeug.exceptions.NotFound()
