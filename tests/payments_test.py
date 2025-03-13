"""Test payment workflow

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import datetime
import pytest
import stripe
import sys

_CLIENT_SECRET = "stripe_client_secret_test"
_EXPIRATION = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
_SIM_TYPE = "srw"
_UID_IN_DB = "J4FHIC7n"


def _skip():
    from sirepo import payments

    return payments.cfg().stripe_secret_key is None


pytestmark = pytest.mark.skipif(_skip(), reason="No Stripe configuration")


def test_auditor(monkeypatch):
    from pykern import pkconfig
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    # Before Sirepo imports
    pkconfig.reset_state_for_testing(
        PKDict(SIREPO_FEATURE_CONFIG_API_MODULES="payments")
    )
    from sirepo import auth_role
    from sirepo import payments
    from sirepo import srdb
    from sirepo import srtime
    from sirepo import srunit
    from sirepo.pkcli import roles
    import asyncio

    pkio.unchecked_remove(srdb.root())
    pkunit.data_dir().join("auditor_db").copy(srdb.root())
    with srunit.quest_start() as qcall:
        qcall.auth_db.model("UserRole").set_role_expiration(
            auth_role.ROLE_PLAN_BASIC, _EXPIRATION, uid=_UID_IN_DB
        )
    with srunit.quest_start() as qcall:
        pkunit.pkeq(
            1,
            len(
                qcall.auth_db.model(
                    "UserSubscription"
                ).active_subscriptions_from_stripe()
            ),
            "expecting just one active subscription",
        )
        monkeypatch.setattr(
            stripe.Subscription,
            "retrieve_async",
            _subscription_active,
        )
        asyncio.run(payments._auditor(None))
    with srunit.quest_start() as qcall:
        monkeypatch.setattr(stripe.Subscription, "retrieve_async", _subscription_unpaid)
        asyncio.run(payments._auditor(None))
    with srunit.quest_start() as qcall:
        pkunit.pkeq(
            0,
            len(
                qcall.auth_db.model(
                    "UserSubscription"
                ).active_subscriptions_from_stripe()
            ),
            "expecting no active subscriptions",
        )
        l = roles.list_with_expiration(_UID_IN_DB)
        for r in l:
            if r.role == auth_role.ROLE_PLAN_BASIC and r.expiration <= srtime.utc_now():
                break
        else:
            pkunit.pkfail(
                "role={} should be expired in roles={}",
                auth_role.ROLE_PLAN_BASIC,
                l,
            )


def test_checkout_session(monkeypatch):
    from pykern import pkconfig
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    # Before Sirepo imports
    pkconfig.reset_state_for_testing(
        PKDict(SIREPO_FEATURE_CONFIG_API_MODULES="payments")
    )
    from sirepo import auth_role
    from sirepo import srdb
    from sirepo import srunit
    from sirepo import util
    from sirepo.pkcli import roles

    monkeypatch.setattr(stripe.checkout.Session, "create_async", _checkout_create)
    monkeypatch.setattr(stripe.checkout.Session, "retrieve_async", _checkout_retrieve)
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve_async",
        _subscription_active,
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


def test_event_paid_webhook(monkeypatch):
    from pykern import pkconfig
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    # Before Sirepo imports
    pkconfig.reset_state_for_testing(
        PKDict(SIREPO_FEATURE_CONFIG_API_MODULES="payments")
    )
    from sirepo import srdb
    from sirepo import srunit

    # TODO(e-carlin): why is this import needed. reset_state_for_testing doesn't work w/o it?
    from sirepo import simulation_db

    monkeypatch.setattr(stripe.Webhook, "construct_event", _webhook_construct)
    monkeypatch.setattr(
        stripe.Subscription,
        "retrieve_async",
        _subscription_active,
    )
    monkeypatch.setattr(stripe.Product, "retrieve_async", _product_retrieve)
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


async def _checkout_retrieve(*args, **kwargs):
    return PKDict(status="complete", subscription=None)


async def _product_retrieve(*args, **kwargs):
    return PKDict(name="test product")


async def _subscription_active(*args, **kwargs):
    from sirepo import payments

    return PKDict(
        id="subscription_id_test",
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
        status="active",
    )


async def _subscription_unpaid(*args, **kwargs):
    from sirepo import payments

    return PKDict(
        metadata=PKDict({payments._STRIPE_SIREPO_UID_METADATA_KEY: _UID_IN_DB}),
        status="unpaid",
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
