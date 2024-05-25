# -*- coding: utf-8 -*-
"""User roles

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkdebug import pkdp
import aenum
import sirepo.feature_config

ROLE_ADM = "adm"
ROLE_USER = "user"
ROLE_PAYMENT_PLAN_ENTERPRISE = "enterprise"
ROLE_PAYMENT_PLAN_PREMIUM = "premium"
PAID_USER_ROLES = (ROLE_PAYMENT_PLAN_PREMIUM, ROLE_PAYMENT_PLAN_ENTERPRISE)
_SIM_TYPE_ROLE_PREFIX = "sim_type_"


class ModerationStatus(aenum.NamedConstant):
    """States used by auth_role_moderation and UserRoleModeration"""

    APPROVE = "approve"
    CLARIFY = "clarify"
    DENY = "deny"
    PENDING = "pending"
    VALID_SET = frozenset([APPROVE, CLARIFY, DENY, PENDING])

    @classmethod
    def check(cls, value):
        assert (
            value in cls.VALID_SET
        ), f"status={value} is not in  valied_set={cls.VALID_SET}"
        return value


def for_moderated_sim_types():
    return [for_sim_type(s) for s in sirepo.feature_config.cfg().moderated_sim_types]


def for_new_user(is_guest):
    if is_guest and pkconfig.in_dev_mode():
        return get_all()
    return [ROLE_USER]


def for_proprietary_oauth_sim_types():
    return [
        for_sim_type(s) for s in sirepo.feature_config.cfg().proprietary_oauth_sim_types
    ]


def for_sim_type(sim_type):
    return _SIM_TYPE_ROLE_PREFIX + sim_type


def get_all():
    return [
        for_sim_type(t) for t in sirepo.feature_config.auth_controlled_sim_types()
    ] + [
        ROLE_ADM,
        ROLE_PAYMENT_PLAN_ENTERPRISE,
        ROLE_PAYMENT_PLAN_PREMIUM,
        ROLE_USER,
    ]


def sim_type(role):
    return role[len(_SIM_TYPE_ROLE_PREFIX) :]
