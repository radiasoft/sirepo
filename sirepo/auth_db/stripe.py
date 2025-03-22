"""Stripe db tables

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sqlalchemy
import sirepo.auth_db

# https://docs.stripe.com/upgrades#what-changes-does-stripe-consider-to-be-backward-compatible
_STRIPE_ID = sqlalchemy.String(255)

_CREATION_REASON_DEFAULT = "payments_checkout_session_status_complete"
_REVOCATION_REASON_INACTIVE_STRIPE_STATUS = "inactive_stripe_status"


class StripePayment(sirepo.auth_db.UserDbBase):
    __tablename__ = "stripe_payment_t"
    user_payment_key = sirepo.auth_db.primary_key_column("spk")
    # Invoice id's are unique in Stripe
    # https://docs.stripe.com/api/invoices/object#invoice_object-id
    invoice_id = sqlalchemy.Column(_STRIPE_ID, unique=True, nullable=False)
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, nullable=False)
    amount_paid = sqlalchemy.Column(sqlalchemy.Integer(), nullable=False)
    created = sqlalchemy.Column(
        sqlalchemy.DateTime(),
        server_default=sqlalchemy.sql.func.now(),
        nullable=False,
    )
    customer_id = sqlalchemy.Column(_STRIPE_ID, nullable=False)
    subscription_id = sqlalchemy.Column(_STRIPE_ID, nullable=False)
    subscription_name = sqlalchemy.Column(_STRIPE_ID, nullable=False)

    def payment_exists(self, invoice_id):
        return self.unchecked_search_by(invoice_id=invoice_id)


class StripeSubscription(sirepo.auth_db.UserDbBase):
    __tablename__ = "stripe_subscription_t"
    stripe_subscription_key = sirepo.auth_db.primary_key_column("ssk")
    uid = sqlalchemy.Column(sirepo.auth_db.STRING_NAME)
    customer_id = sqlalchemy.Column(_STRIPE_ID, nullable=False)
    checkout_session_id = sqlalchemy.Column(_STRIPE_ID, nullable=True)
    subscription_id = sqlalchemy.Column(_STRIPE_ID, nullable=False)
    creation_reason = sqlalchemy.Column(
        sirepo.auth_db.STRING_NAME,
        server_default=_CREATION_REASON_DEFAULT,
    )
    created = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=False)
    revocation_reason = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, nullable=True)
    revoked = sqlalchemy.Column(sqlalchemy.DateTime(), nullable=True)
    role = sqlalchemy.Column(sirepo.auth_db.STRING_NAME, nullable=False)

    def not_revoked_stripe_subscriptions(self):
        return self.unchecked_search_all(
            revoked=None,
            creation_reason=_CREATION_REASON_DEFAULT,
        )

    def revoke_due_to_inactive_stripe_status(self, subscription_record):
        s = self._new(subscription_record)
        s.revocation_reason = _REVOCATION_REASON_INACTIVE_STRIPE_STATUS
        s.revoked = sirepo.srtime.utc_now()
        s.save()
