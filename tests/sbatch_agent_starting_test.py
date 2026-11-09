"""test sbatch agent start taking longer than agent_starting_secs

Separate from sbatch_test, because of the config.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest

# The ssh start script and the agent connecting take seconds, which is longer
# than this
pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        cfg=PKDict(
            SIREPO_JOB_DRIVER_SBATCH_AGENT_STARTING_SECS="0",
        ),
    ),
)


def test_srw_agent_start_longer_than_agent_starting_secs(new_user_fc):
    """The timer for the agent to connect covers the ssh start

    It starts before the ssh start script runs. If it only allows
    agent_starting_secs, it frees the agent that the script just started,
    which destroys the sbatch_login op.
    """
    # POSIT: tests/sbatch_test.py is in the same directory
    import sbatch_test

    f = new_user_fc
    d, c = sbatch_test._srw_login(f)
    f.sr_run_sim(d, c, expect_completed=False, timeout=5)
