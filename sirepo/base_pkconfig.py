# -*- coding: utf-8 -*-
u"""Default config

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

def alpha():
    return {}


def beta():
    return {}


def dev():
    return {
        'sirepo': {
            'runner_daemon': {
                'docker_process': {
                    'dev_env_in_container': True,
                },
            },
        },
    }

def prod():
    return {}
