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
import stripe

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
                                "price": _plan_to_price(
                                    self.sreq.form_get("plan", "uknown")
                                ),
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
                        client_reference_id=u,
                        # TODO(e-carlin): needed?
                        # automatic_tax=PKDict(enabled=True),
                    )
                ).client_secret,
            ),
        )

    @sirepo.quest.Spec("require_user")
    async def api_paymentCheckoutSessionStatus(self):
        return self.reply_ok(
            PKDict(
                sessionStatus=(
                    await stripe.checkout.Session.retrieve_async(
                        self.body_as_dict().sessionId,
                    )
                ).status
            )
        )

    @sirepo.quest.Spec("allow_visitor")
    async def api_stripeWebhook(self):
        def _get_role(subscription):
            return PKDict(
                {
                    cfg().stripe_plan_basic_price_id: sirepo.auth_role.ROLE_PLAN_BASIC,
                    cfg().stripe_plan_premium_price_id: sirepo.auth_role.ROLE_PLAN_PREMIUM,
                }
            )[subscription["items"].data[0].price.id]

        if not cfg().stripe_webhook_secret:
            raise AssertionError(
                "must define stripe_webhook_secret to call api_stripeWebhook"
            )
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
            self.auth_db.model("UserRole").add_roles(
                roles=[_get_role(s)],
                expiration=datetime.datetime.fromtimestamp(s.current_period_end),
                # TODO(e-carlin): should we validate against our db? We don't have
                # a foreign key relationship setup with user_registration_t
                uid=s.metadata[_STRIPE_SIREPO_UID_METADATA_KEY],
            )
        return self.reply_ok()


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
