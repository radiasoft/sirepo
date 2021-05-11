# -*- coding: utf-8 -*-
u"""User roles

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
import sirepo.feature_config

ROLE_ADM = 'adm'
ROLE_PAYMENT_PLAN_ENTERPRISE = 'enterprise'
ROLE_PAYMENT_PLAN_PREMIUM = 'premium'

PAID_USER_ROLES = (ROLE_PAYMENT_PLAN_PREMIUM, ROLE_PAYMENT_PLAN_ENTERPRISE)


def for_new_user(is_guest):
    if is_guest and pkconfig.channel_in('dev'):
        return get_all()
    return [for_sim_type(x) for x in sirepo.feature_config.cfg().default_proprietary_sim_types]


def get_all():
    return [
        for_sim_type(t) for t in sirepo.feature_config.auth_controlled_sim_types()
    ] + [
        ROLE_ADM,
        ROLE_PAYMENT_PLAN_ENTERPRISE,
        ROLE_PAYMENT_PLAN_PREMIUM,
    ]


def for_sim_type(sim_type):
    return 'sim_type_' + sim_type
