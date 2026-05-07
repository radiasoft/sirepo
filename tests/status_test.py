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
            SIREPO_STATUS_SIM_RANDOM="dog.weight",
        ),
    ),
)


def test_basic(auth_fc):
    from pykern import pkcompat
    from pykern.pkunit import pkeq
    import base64

    def _headers(uid):
        return PKDict(
            Authorization="Basic "
            + pkcompat.from_bytes(
                base64.b64encode(
                    pkcompat.to_bytes(f"{uid}:pass"),
                ),
            ),
        )

    def _status(fc, headers, timestamps, delay=0):
        import time

        if delay:
            time.sleep(delay)
        r = fc.sr_get_json("serverStatus", headers=headers)
        pkeq("ok", r.state)
        pkeq("unique-value", r.sentinel)
        timestamps.append(r.datetime)

    # POSIT: sirepo.auth.basic.require_user returns logged_in_user in srunit
    u = auth_fc.sr_login_as_guest()
    auth_fc.sr_logout()
    t = []
    for i in range(10):
        auth_fc.sr_thread_start(
            f"t{i}", _status, headers=_headers(u), timestamps=t, delay=i * 0.5
        )
    auth_fc.sr_thread_join()
    pkeq(10, len(t))
