"""Payment handling with Stripe

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdformat
import datetime
import sirepo.auth_role
import sirepo.quest
import sqlalchemy
import stripe
import sirepo.srtime

from uri_router import _validate_root_redirect_uris

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
                            {
                                "price": _plan_to_price(self.body_as_dict().plan),
                                "quantity": 1,
                            },
                        ],
                        mode="subscription",
                        subscription_data=PKDict(
                            metadata=PKDict({_STRIPE_SIREPO_UID_METADATA_KEY: u})
                        ),
                        return_url=self.absolute_uri(
                            sirepo.uri.local_route(
                                self.parse_post().type,
                                route_name="paymentFinalization",
                                query=PKDict(session_id="{CHECKOUT_SESSION_ID}"),
                                query_safe_chars="{}",
                            )
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

        def _res():
            return self.reply_ok(PKDict(sessionStatus=s))

        s = (
            await stripe.checkout.Session.retrieve_async(
                self.body_as_dict().sessionId,
            )
        ).status
        if not s == "complete":
            return _res()

        self.auth_db.model("UserSubscription").new(
            # TODO(e-carlin): which uid? the one from subscription is more secure (bound to the session id)
            # but idk if we have access to it at this point.
            uid=self.auth.logged_in_user(),
            uid=subscription.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
            checkout_session_id=self.body_as_dict().sessionId,
            creation_reason=self.auth_db.model(
                "UserSubscription"
            ).CREATION_REASON_CHECKOUT_SESSION_STATUS_COMPLETE,
            created=sirepo.srtime.utc_now(),
            revocation_reason=None,
            revoked=None,
            role=_price_to_role(subscription),
        ).save()
        # SECURITY: There is potential here for someone to get a session id
        # and then call this API to create a role for themselves. Session ID's
        # aren't secret but to get one in a state of 'complete' would require
        # work and they aren't easily guessable so it is fairly secure.

        # We aren't 100% positive the user has fully paid at this
        # point. But, we are pretty sure. So, proactively give them the
        # role and the payment cron will remove if it finds out they
        # didn't end up paying
        # TODO(e-carlin): change "payment cron" to whatever the name actually is
        # TODO(e-carlin): how do we get subscription?
        self.auth_db.model("UserRole").add_roles(
            roles=[_price_to_role(subscription)],
            expiration=datetime.datetime.fromtimestamp(subscription.current_period_end),
            # TODO(e-carlin): should we validate against our db? We don't have
            # a foreign key relationship setup with user_registration_t
            # TODO(e-carlin): maybe just logged_in_user()?
            uid=subscription.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
        )
        return _res()

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
            self.auth_db.model("UserPayment").new(
                amount_paid=e["data"]["object"]["amount_paid"],
                customer_id=e["data"]["object"]["customer"],
                invoice_id=e["data"]["object"]["id"],
                subscription_id=e["data"]["object"]["subscription"],
                subscription_name=(
                    await stripe.Product.retrieve_async(
                        s["items"].data[0]["price"]["product"]
                    )
                )["name"],
                uid=s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
            ).save()
        return self.reply_ok()


def init_apis(*args, **kwargs):
    # TODO(e-carlin): start cron
    pass


def cfg():
    global _cfg

    if _cfg:
        return _cfg
    _cfg = pkconfig.init(
        stripe_secret_key=pkconfig.Required(str, "Stripe secret API key"),
        stripe_publishable_key=pkconfig.Required(str, "Stripe publishable API key"),
        stripe_plan_basic_price_id=pkconfig.Required(
            str, "Stripe price ID for basic plan"
        ),
        stripe_plan_premium_price_id=pkconfig.Required(
            str, "Stripe price ID for premium plan"
        ),
        # In dev stripe cli will output this
        stripe_webhook_secret=pkconfig.RequiredUnlessDev(
            None, str, "Stripe secret key for webhook security"
        ),
    )
    stripe.api_key = _cfg.stripe_secret_key
    # Explicitly setting like this forces stripe to raise an error if
    # a sync call is ever called when there is a corresponding async
    # method available.
    stripe.default_http_client = stripe.HTTPXClient()
    return _cfg
