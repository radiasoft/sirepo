"""test server status

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest

pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        cfg=PKDict(
            SIREPO_STATUS_REPLY_SENTINEL="unique-value",
            SIREPO_STATUS_SIM_NAME="Scooby Doo",
            SIREPO_STATUS_SIM_REPORT="heightWeightReport",
            SIREPO_STATUS_SIM_TYPE="myapp",
        ),
    ),
)


def test_basic(auth_fc):
    from pykern import pkconfig, pkcompat
    from pykern.pkunit import pkeq
    from sirepo import srunit
    import base64

    def _status(fc, headers):
        r = fc.sr_get_json("serverStatus", headers=headers)
        pkeq("ok", r.state)
        pkeq("unique-value", r.sentinel)

    # POSIT: sirepo.auth.basic.require_user returns logged_in_user in srunit
    u = auth_fc.sr_login_as_guest()
    auth_fc.sr_logout()
    h = PKDict(
        Authorization="Basic "
        + pkcompat.from_bytes(
            base64.b64encode(
                pkcompat.to_bytes(f"{u}:pass"),
            ),
        ),
    )
    auth_fc.sr_thread_start("t1", _status, headers=h)
    auth_fc.sr_thread_start("t2", _status, headers=h)
    #    auth_fc.sr_thread_start("t3", _status, headers=h)
    auth_fc.sr_thread_join()
