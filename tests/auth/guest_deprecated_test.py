"""Test deprecated auth.guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest
from pykern.pkcollections import PKDict

_sim_type = "myapp"
pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        cfg=PKDict(
            SIREPO_AUTH_DEPRECATED_METHODS="guest",
            SIREPO_SMTP_FROM_EMAIL="x@x.x",
            SIREPO_SMTP_FROM_NAME="x",
            SIREPO_SMTP_PASSWORD="x",
            SIREPO_SMTP_SERVER="dev",
            SIREPO_SMTP_USER="x",
            SIREPO_AUTH_GUEST_EXPIRY_DAYS="1",
            SIREPO_AUTH_METHODS="email",
            SIREPO_FEATURE_CONFIG_SIM_TYPES=_sim_type,
        ),
    ),
)


def test_deprecated(fc_module):
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern.pkdebug import pkdp

    fc_module.sr_get_root(_sim_type)
    fc_module.sr_get(
        "authGuestLogin", {"simulation_type": _sim_type}, redirect=False
    ).assert_http_redirect("guest/deprecated")
