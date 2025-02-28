"""Payment handling with Stripe

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc
import sirepo.quest
import stripe

_cfg = None


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_user")
    async def api_paymentCreateCheckoutSession(self):
        """Create a Stripe checkout session

        Returns:
            str: Stripe client secret
        """
        return self.reply_ok(
            PKDict(
                clientSecret=(
                    await stripe.checkout.Session.create_async(
                        customer_email=self.auth.user_name(self.auth.logged_in_user()),
                        ui_mode="embedded",
                        line_items=[
                            {
                                # TODO(e-carlin): handle premium plan
                                "price": _cfg.stripe_basic_plan_price_id,
                                "quantity": 1,
                            },
                        ],
                        mode="subscription",
                        # TODO(e-carlin): need to fix this. See moss. Need to add {CHECKOUT_SESSION_ID}  prob sim type
                        return_url="http://localhost:8000",
                        # TODO(e-carlin): don't think this is needed
                        # client_reference_id=uid,
                        # TODO(e-carlin): needed?
                        # automatic_tax=PKDict(enabled=True),
                    )
                ).client_secret,
            ),
        )


def init_apis(*args, **kwargs):
    global _cfg

    if _cfg:
        return
    _cfg = pkconfig.init(
        stripe_secret_key=pkconfig.Required(str, "Stripe secret API key"),
        stripe_publishable_key=pkconfig.Required(str, "Stripe publishable API key"),
        stripe_basic_plan_price_id=pkconfig.Required(
            str, "Stripe price ID for basic plan"
        ),
        stripe_premium_plan_price_id=pkconfig.Required(
            str, "Stripe price ID for premium plan"
        ),
    )
    stripe.api_key = _cfg.stripe_secret_key
    # Explicitly setting like this forces stripe to raise an error if
    # a sync call is ever called when there is a corresponding async
    # method available.
    stripe.default_http_client = stripe.HTTPXClient()
