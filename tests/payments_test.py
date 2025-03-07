"""Test payment workflow

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import datetime
import pytest
import sys

_EXPIRATION = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
_SIM_TYPE = "srw"
_UID_IN_DB = "bkDZ1K1F"

sys.modules["stripe"] = pkinspect.this_module()


class Webhook:
    @classmethod
    def construct_event(cls, *args, **kwargs):
        return PKDict(
            type="invoice.paid",
            data=PKDict(object=PKDict(subscription=PKDict())),
        )


class Subscription:
    @classmethod
    async def retrieve_async(*args, **kwargs):
        from sirepo import payments

        return PKDict(
            items=PKDict(
                data=[
                    PKDict(price=PKDict(id=payments.cfg().stripe_plan_basic_price_id))
                ]
            ),
            current_period_end=_EXPIRATION.timestamp(),
            metadata=PKDict({payments._STRIPE_SIREPO_UID_METADATA_KEY: _UID_IN_DB}),
        )


class HTTPXClient:
    pass


def _skip():
    from sirepo import payments

    return payments.cfg().stripe_secret_key is None


pytestmark = pytest.mark.skipif(_skip(), reason="No Stripe configuration")


def test_new_create_checkout_session(stripe_auth_fc):
    from sirepo import auth_role
    from pykern.pkunit import pkre

    stripe_auth_fc.sr_email_login("e@e.e")
    stripe_auth_fc.add_plan_trial_role()
    res = stripe_auth_fc.sr_post(
        "paymentCreateCheckoutSession",
        PKDict(simulationType=_SIM_TYPE, plan=auth_role.ROLE_PLAN_BASIC),
    )
    pkre("^cs_test_", res.clientSecret)


def test_event_paid_webhook():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import auth_role
    from sirepo import srdb
    from sirepo import srunit
    from sirepo.pkcli import roles

    pkio.unchecked_remove(srdb.root())
    pkunit.data_dir().join("db").copy(srdb.root())
    l = roles.list(_UID_IN_DB)
    pkunit.pkok(
        auth_role.ROLE_PLAN_BASIC not in set(l),
        "{} role found in roles={}",
        auth_role.ROLE_PLAN_BASIC,
        l,
    )
    with srunit.quest_start() as qcall:

        r = qcall.call_api_sync("stripeWebhook", body=PKDict())
        pkunit.pkeq("ok", r.content_as_object().state)
        l = roles.list_with_expiration(_UID_IN_DB)
        for r in l:
            if r.role == auth_role.ROLE_PLAN_BASIC:
                pkunit.pkeq(_EXPIRATION, r.expiration)
                return
        pkunit.pkfail(
            "no role={}  with expiration={} in roles={}",
            auth_role.ROLE_PLAN_BASIC,
            _EXPIRATION,
            l,
        )
