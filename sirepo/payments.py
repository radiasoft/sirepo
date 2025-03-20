"""Payment handling with Stripe

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdformat
import datetime
import sirepo.auth_db.user
import sirepo.auth_role
import sirepo.cron
import sirepo.quest
import sirepo.srtime
import sirepo.util
import stripe

_CHECKOUT_SESSION_ID_URI_PARAM = "~CHECKOUT_SESSION_ID~"
#: keep reference so auditor isn't garbage collected
_ROLE_AUDITOR_CRON = None
_ROLE_CREATED_BY_API_CHECKOUT_SESSION_STATUS = (
    sirepo.auth_db.user.UserSubscription.CREATION_REASON_CHECKOUT_SESSION_STATUS_COMPLETE
)
_STRIPE_ACTIVE_SUBSCRIPTION_STATUSES = {"trialing", "active", "past_due"}
_STRIPE_SIGNATURE_HEADER = "Stripe-Signature"
_STRIPE_SIREPO_UID_METADATA_KEY = "sirepo_uid"
_cfg = None


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_user")
    async def api_paymentCreateCheckoutSession(self):
        """Create a Stripe checkout session

        Returns:
            str: Stripe client secret
        """

        def _plan_to_price(plan):
            return PKDict(
                {
                    sirepo.auth_role.ROLE_PLAN_BASIC: cfg().stripe_plan_basic_price_id,
                    sirepo.auth_role.ROLE_PLAN_PREMIUM: cfg().stripe_plan_premium_price_id,
                }
            )[plan]

        u = self.auth.logged_in_user()
        return self.reply_ok(
            PKDict(
                clientSecret=(
                    await stripe.checkout.Session.create_async(
                        customer_email=self.auth.user_name(u),
                        ui_mode="embedded",
                        line_items=[
                            PKDict(
                                price=_plan_to_price(self.body_as_dict().plan),
                                quantity=1,
                            ),
                        ],
                        mode="subscription",
                        subscription_data=PKDict(
                            metadata=PKDict({_STRIPE_SIREPO_UID_METADATA_KEY: u}),
                        ),
                        return_url=self.absolute_uri(
                            sirepo.uri.local_route(
                                self.parse_post().type,
                                route_name="paymentFinalization",
                                query=PKDict(session_id=_CHECKOUT_SESSION_ID_URI_PARAM),
                            )
                        ).replace(
                            _CHECKOUT_SESSION_ID_URI_PARAM, "{CHECKOUT_SESSION_ID}"
                        ),
                        # TODO(e-carlin): needed?
                        # automatic_tax=PKDict(enabled=True),
                    )
                ).client_secret,
            ),
        )

    @sirepo.quest.Spec("require_user")
    async def api_paymentCheckoutSessionStatus(self):
        def _price_to_role(subscription):
            return PKDict(
                {
                    cfg().stripe_plan_basic_price_id: sirepo.auth_role.ROLE_PLAN_BASIC,
                    cfg().stripe_plan_premium_price_id: sirepo.auth_role.ROLE_PLAN_PREMIUM,
                }
            )[subscription["items"].data[0].price.id]

        def _res(checkout_session):
            return self.reply_ok(PKDict(sessionStatus=checkout_session.status))

        b = self.body_as_dict()
        c = await stripe.checkout.Session.retrieve_async(
            b.sessionId,
        )
        if not c.status == "complete":
            return _res(c)
        s = await stripe.Subscription.retrieve_async(c.subscription)
        if (
            not s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY]
            == self.auth.logged_in_user()
        ):
            raise AssertionError(
                f"stripe_uid={s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY]} does not match logged_in_user={self.auth.logged_in_user()}"
            )
        self.auth_db.model("UserSubscription").new(
            uid=s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
            stripe_customer_id=s.customer,
            stripe_checkout_session_id=b.sessionId,
            stripe_subscription_id=s.id,
            creation_reason=_ROLE_CREATED_BY_API_CHECKOUT_SESSION_STATUS,
            created=sirepo.srtime.utc_now(),
            revocation_reason=None,
            revoked=None,
            role=_price_to_role(s),
        ).save()
        # We aren't 100% positive the user has fully paid at this
        # point. But, we are pretty sure. So, proactively give them the
        # role and _ROLE_AUDITOR_CRON will remove if it finds out they
        # didn't end up paying.
        self.auth_db.model("UserRole").add_roles(
            roles=[_price_to_role(s)],
            expiration=datetime.datetime.fromtimestamp(s.current_period_end),
            uid=s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
        )
        return _res(c)

    @sirepo.quest.Spec("allow_visitor")
    async def api_paymentPlanRedirect(self, plan):
        raise sirepo.util.Redirect(
            sirepo.uri.local_route(
                sirepo.util.first_sim_type(),
                route_name="paymentCheckout",
                query=PKDict(plan=plan),
            ),
        )

    @sirepo.quest.Spec("allow_visitor")
    async def api_stripeWebhook(self):
        # https://docs.stripe.com/billing/subscriptions/webhooks
        # TODO(e-carlin): need to add our api to stripe dashboard https://docs.stripe.com/webhooks#test-webhook
        e = stripe.Webhook.construct_event(
            self.sreq.body_as_bytes(),
            self.sreq.header_uget(_STRIPE_SIGNATURE_HEADER),
            cfg().stripe_webhook_secret,
        )
        if e and e["type"] == "invoice.paid":
            s = await stripe.Subscription.retrieve_async(
                e["data"]["object"]["subscription"]
            )
            if not len(s["items"].data) == 1:
                raise AssertionError(
                    pkdformat("multiple subscription line items s={}", s)
                )
            n = (
                await stripe.Product.retrieve_async(
                    s["items"].data[0]["price"]["product"]
                )
            )["name"]
            # Be robust against stripe sending duplicate events.
            # No await below here so we are sure only one call makes
            # it through.
            # https://docs.stripe.com/webhooks#handle-duplicate-events
            if self.auth_db.model("UserPayment").payment_exists(
                e["data"]["object"]["id"]
            ):
                return self.reply_ok()
            self.auth_db.model("UserPayment").new(
                stripe_amount_paid=e["data"]["object"]["amount_paid"],
                stripe_customer_id=e["data"]["object"]["customer"],
                stripe_invoice_id=e["data"]["object"]["id"],
                stripe_subscription_id=e["data"]["object"]["subscription"],
                stripe_subscription_name=n,
                uid=s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
            ).save()
        return self.reply_ok()


def init_apis(*args, **kwargs):
    global _ROLE_AUDITOR_CRON

    _ROLE_AUDITOR_CRON = sirepo.cron.CronTask(
        cfg().role_auditor_cron_period, _auditor, None
    )
    pass


def cfg():
    global _cfg

    if _cfg:
        return _cfg
    _cfg = pkconfig.init(
        role_auditor_cron_period=(
            60 * 60 * 24,
            int,
            "Seconds to sleep between runs of auditor",
        ),
        stripe_secret_key=pkconfig.Required(str, "Stripe secret API key"),
        stripe_publishable_key=pkconfig.Required(str, "Stripe publishable API key"),
        stripe_plan_basic_price_id=pkconfig.Required(
            str, "Stripe price ID for basic plan"
        ),
        stripe_plan_premium_price_id=pkconfig.Required(
            str, "Stripe price ID for premium plan"
        ),
        # In dev stripe cli will output this
        stripe_webhook_secret=pkconfig.Required(
            str, "Stripe secret key for webhook security"
        ),
    )
    stripe.api_key = _cfg.stripe_secret_key
    # Explicitly setting like this forces stripe to raise an error if
    # a sync call is ever called when there is a corresponding async
    # method available.
    stripe.default_http_client = stripe.HTTPXClient()
    return _cfg


async def _auditor(_):
    """Remove sriepo subscription/role for users with inactive Stripe subscription status.

    We proactively assign roles from
    api_paymentCheckoutSessionStatus. This auditor goes through
    all sirepo subscriptions/roles created by that API and revokes
    any that are not active in Stripe.
    """

    async def _stripe_status_is_active(subscription_record):
        s = await stripe.Subscription.retrieve_async(
            subscription_record.stripe_subscription_id
        )
        if s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY] != subscription_record.uid:
            raise AssertionError(
                pkdformat(
                    "subscription={} not bound to uid={}",
                    s,
                    subscription_record.uid,
                )
            )
        return s.status in _STRIPE_ACTIVE_SUBSCRIPTION_STATUSES

    with sirepo.quest.start() as qcall:
        for s in qcall.auth_db.model(
            "UserSubscription"
        ).non_revoked_stripe_subscriptions():
            if qcall.auth_db.model("UserRole").has_expired_role(s.role, uid=s.uid):
                continue
            if await _stripe_status_is_active(
                s,
            ):
                continue
            pkdlog("revoking uid={} role={}", s.uid, s.role)
            qcall.auth_db.model("UserRole").expire_role(s.role, uid=s.uid)
            qcall.auth_db.model(
                "UserSubscription"
            ).revoke_due_to_inactive_stripe_status(s)
