# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import copy


SIM_TYPE = 'adm'

# stubbed data for testing
def get_server_data(id):

    data = [
        ['jobId', 'jobStart', 'jobState', 'jobReport'],
        ['123', '2018-10-03T16:09:09+00:05', 'running', 'foo & bar'],
        ['456', '2018-10-01T16:21:09+00:05', 'complete', 'TITLE 456']
    ];
    if id == None:
        return data

    if str(id) == '123':
        return [
            data[0],
            data[1],
        ]
    if str(id) == '456':
        return [
            data[0],
            data[2],
        ]

    return []
