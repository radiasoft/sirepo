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
            dict: Stripe checkout session ID
        """
        email = self.auth.user_name(self.auth.logged_in_user())
        checkout_session = await stripe.checkout.Session.create_async(
            customer_email=email,
            ui_mode="embedded",
            line_items=[
                {
                    "price": _cfg.stripe_price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            # TODO(e-carlin): need to fix this. See moss. Need to add {CHECKOUT_SESSION_ID}  prob sim type
            return_url="http://localhost:8000",
            # TODO(e-carlin): don't think this is needed
            # client_reference_id=uid,
        )
        return self.reply_dict(id=checkout_session.id)


def init_apis(*args, **kwargs):
    global _cfg

    if _cfg:
        return
    _cfg = pkconfig.init(
        stripe_api_key=(None, str, "Stripe API key"),
        stripe_webhook_secret=(None, str, "Stripe webhook secret"),
        stripe_price_id=(None, str, "Stripe price ID for premium plan"),
        stripe_publishable_key=(None, str, "Stripe publishable key for frontend"),
    )
    if _cfg.stripe_api_key:
        stripe.api_key = _cfg.stripe_api_key
        # TODO(e-carlin): make stripe api key requried and set async

    # Explicitly setting like this forces stripe to raise an error if
    # a sync call is ever called when there is a corresponding async
    # method available.
    stripe.default_http_client = stripe.HTTPXClient()
