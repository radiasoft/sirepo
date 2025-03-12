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

_CLIENT_SECRET = "stripe_client_secret_test"
_EXPIRATION = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
_SIM_TYPE = "srw"
# TODO(e-carlin): I'm not convinced we need to have an _data db
_UID_IN_DB = "J4FHIC7n"

sys.modules["stripe"] = pkinspect.this_module()


async def _checkout_retrieve(*args, **kwargs):
    return PKDict(status="complete", subscription=None)


async def _checkout_create(**kwargs):
    from pykern import pkunit
    from sirepo import payments

    pkunit.pkeq(
        _UID_IN_DB,
        kwargs["subscription_data"].metadata[payments._STRIPE_SIREPO_UID_METADATA_KEY],
    )
    pkunit.pkeq(
        payments.cfg().stripe_plan_basic_price_id,
        kwargs["line_items"][0]["price"],
    )
    return PKDict(client_secret=_CLIENT_SECRET)


checkout = PKDict(
    Session=PKDict(retrieve_async=_checkout_retrieve, create_async=_checkout_create)
)


def _webhook_construct(*args, **kwargs):
    return PKDict(
        type="invoice.paid",
        data=PKDict(
            object=PKDict(
                id="id_test",
                amount_paid=1,
                customer="customer_id_test",
                subscription="subscription_id_test",
            )
        ),
    )


Webhook = PKDict(construct_event=_webhook_construct)


class Product:
    @classmethod
    async def retrieve_async(*args, **kwargs):
        return PKDict(name="test product")


class Subscription:
    @classmethod
    async def retrieve_async(*args, **kwargs):
        from sirepo import payments

        return PKDict(
            customer="customer_id_test",
            items=PKDict(
                data=[
                    PKDict(
                        price=PKDict(
                            id=payments.cfg().stripe_plan_basic_price_id,
                            product="test product",
                        )
                    )
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


# TODO(e-carlin): no more uses of stripe_auth_fc. I think I can remove it. srunit or conftest?
def test_checkout_session():
    from pykern import pkconfig
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import auth_role
    from sirepo import srdb
    from sirepo import srunit
    from sirepo import util
    from sirepo.pkcli import roles

    # TODO(e-carlin): this doesn't seem to do anything
    pkconfig.reset_state_for_testing(
        PKDict(SIREPO_FEATURE_CONFIG_API_MODULES="payments")
    )
    pkio.unchecked_remove(srdb.root())
    pkunit.data_dir().join("db").copy(srdb.root())
    with srunit.quest_start() as qcall:
        qcall.cookie.set_sentinel()
        try:
            r = qcall.auth.login(method="guest", uid=_UID_IN_DB, sim_type="myapp")
            pkunit.pkfail("expecting sirepo.util.SReplyExc")
        except util.SReplyExc as e:
            pass
        r = qcall.call_api_sync(
            "paymentCreateCheckoutSession",
            body=PKDict(simulationType=_SIM_TYPE, plan=auth_role.ROLE_PLAN_BASIC),
        )
        pkunit.pkre(rf"^{_CLIENT_SECRET}$", r.content_as_object().clientSecret)
        r = qcall.call_api_sync(
            "paymentCheckoutSessionStatus",
            body=PKDict(sessionId="session_id_test"),
        )
        l = roles.list_with_expiration(_UID_IN_DB)
        for r in l:
            if r.role == auth_role.ROLE_PLAN_BASIC and r.expiration == _EXPIRATION:
                break
        else:
            pkunit.pkfail(
                "no role={} with expiration={} in roles={}",
                auth_role.ROLE_PLAN_BASIC,
                _EXPIRATION,
                l,
            )
        pkunit.pkok(
            qcall.auth_db.model("UserSubscription").search_by(uid=_UID_IN_DB),
            "expecting a UserSubscription record",
        )


def test_event_paid_webhook():
    from pykern import pkio
    from pykern import pkunit
    from pykern import pkconfig
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import srdb
    from sirepo import srunit

    # TODO(e-carlin): this doesn't seem to do anything
    pkconfig.reset_state_for_testing(
        PKDict(SIREPO_FEATURE_CONFIG_API_MODULES="payments")
    )
    pkio.unchecked_remove(srdb.root())
    pkunit.data_dir().join("db").copy(srdb.root())
    with srunit.quest_start() as qcall:
        r = qcall.call_api_sync("stripeWebhook", body=PKDict())
        pkunit.pkeq("ok", r.content_as_object().state)
        pkunit.pkok(
            qcall.auth_db.model("UserPayment").search_by(uid=_UID_IN_DB),
            "no UserPayment record for uid={}",
            _UID_IN_DB,
        )
