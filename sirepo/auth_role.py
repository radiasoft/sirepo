# -*- coding: utf-8 -*-
u"""User roles

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkdebug import pkdp
import sirepo.feature_config

ROLE_ADM = 'adm'
ROLE_PAYMENT_PLAN_ENTERPRISE = 'enterprise'
ROLE_PAYMENT_PLAN_PREMIUM = 'premium'
PAID_USER_ROLES = (ROLE_PAYMENT_PLAN_PREMIUM, ROLE_PAYMENT_PLAN_ENTERPRISE)
_SIM_TYPE_ROLE_PREFIX = 'sim_type_'


def for_moderated_sim_types():
    return [for_sim_type(s) for s in sirepo.feature_config.cfg().moderated_sim_types]


def for_new_user(is_guest):
    if is_guest and pkconfig.channel_in('dev'):
        return get_all()
    return []


def for_proprietary_oauth_sim_types():
    return [for_sim_type(s) for s in sirepo.feature_config.cfg().proprietary_oauth_sim_types]


def for_sim_type(sim_type):
    return _SIM_TYPE_ROLE_PREFIX + sim_type


def get_all():
    return [
        for_sim_type(t) for t in sirepo.feature_config.auth_controlled_sim_types()
    ] + [
        ROLE_ADM,
        ROLE_PAYMENT_PLAN_ENTERPRISE,
        ROLE_PAYMENT_PLAN_PREMIUM,
    ]


def sim_type(role):
    return role[len(_SIM_TYPE_ROLE_PREFIX):]
