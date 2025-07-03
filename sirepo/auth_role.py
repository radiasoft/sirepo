"""User roles

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkinspect
from pykern import pkunit
from pykern.pkdebug import pkdp
import aenum
import sirepo.feature_config

ROLE_ADM = "adm"
ROLE_PLAN_BASIC = "basic"
ROLE_PLAN_PREMIUM = "premium"
ROLE_PLAN_TRIAL = "trial"
ROLE_USER = "user"
PLAN_ROLES_PAID = frozenset((ROLE_PLAN_BASIC, ROLE_PLAN_PREMIUM))
PLAN_ROLES = PLAN_ROLES_PAID.union([ROLE_PLAN_TRIAL])
_SIM_TYPE_ROLE_PREFIX = "sim_type_"

_FOR_NEW_USER = frozenset((ROLE_USER,))

_ADM_SET = frozenset([ROLE_ADM])


class ModerationStatus(aenum.NamedConstant):
    """States used by auth_role_moderation and UserRoleModeration"""

    APPROVE = "approve"
    CLARIFY = "clarify"
    DENY = "deny"
    PENDING = "pending"
    VALID_SET = frozenset([APPROVE, CLARIFY, DENY, PENDING])

    @classmethod
    def check(cls, value):
        if value not in cls.VALID_SET:
            raise AssertionError(
                f"status={value} is not in  valied_set={cls.VALID_SET}"
            )
        return value


def check(role):
    if role not in _all():
        raise AssertionError(f"invalid role={role}")
    return role


def for_moderated_sim_types():
    return _memoize(_for_sim_types("moderated_sim_types"))


def for_new_user(auth_method):
    from sirepo import auth

    if pkconfig.in_dev_mode:
        if auth_method == auth.METHOD_GUEST:
            return _all()
        if auth_method != auth.METHOD_EMAIL and pkunit.is_test_run():
            return _all() - _ADM_SET
    rv = _FOR_NEW_USER
    if not sirepo.feature_config.have_payments():
        return rv.union([ROLE_PLAN_PREMIUM])
    return rv


def for_proprietary_oauth_sim_types():
    return _memoize(_for_sim_types("proprietary_oauth_sim_types"))


def for_sim_type(sim_type):
    return check(_unchecked_for_sim_type(sim_type))


def sim_type(role):
    if not check(role).startswith(_SIM_TYPE_ROLE_PREFIX):
        raise AssertionError(f"not a sim_type role={role}")
    return role[len(_SIM_TYPE_ROLE_PREFIX) :]


def _all():
    return _memoize(
        _for_sim_types("auth_controlled_sim_types").union(
            (
                ROLE_ADM,
                ROLE_PLAN_BASIC,
                ROLE_PLAN_PREMIUM,
                ROLE_PLAN_TRIAL,
                ROLE_USER,
            )
        ),
    )


def _for_sim_types(attr):
    # a bit goofy, but simplified above
    if (x := sirepo.feature_config.cfg().get(attr)) is None:
        x = getattr(sirepo.feature_config, attr)()
    return frozenset(_unchecked_for_sim_type(s) for s in x)


def _memoize(value):
    def wrap():
        return value

    setattr(pkinspect.this_module(), pkinspect.caller_func_name(), wrap)
    return value


def _unchecked_for_sim_type(sim_type):
    return _SIM_TYPE_ROLE_PREFIX + sim_type
