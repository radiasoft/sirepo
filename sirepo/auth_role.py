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
ROLE_PLAN_BASIC = "basic"
ROLE_PLAN_PREMIUM = "premium"
ROLE_PLAN_TRIAL = "trial"
ROLE_USER = "user"
PLAN_ROLES_PAID = frozenset((ROLE_PLAN_BASIC, ROLE_PLAN_PREMIUM))
PLAN_ROLES = PLAN_ROLES_PAID.union((ROLE_PLAN_TRIAL,))
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


def for_new_user(auth_method):
    import sirepo.auth

    if pkconfig.in_dev_mode:
        if auth_method == sirepo.auth.METHOD_GUEST:
            return get_all()
        # the email auth method on dev has limited roles for unit tests
        if auth_method != sirepo.auth.METHOD_EMAIL:
            return list(filter(lambda r: r != ROLE_ADM, get_all()))
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
        ROLE_PLAN_BASIC,
        ROLE_PLAN_PREMIUM,
        ROLE_PLAN_TRIAL,
        ROLE_USER,
    ]


def sim_type(role):
    return role[len(_SIM_TYPE_ROLE_PREFIX) :]
