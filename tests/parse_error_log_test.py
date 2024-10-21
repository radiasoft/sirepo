"""Parsing of an error run.log

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os


def setup_module(module):
    os.environ.update(
        # Dev mode has to be false for these tests to pass
        PYKERN_PKCONFIG_DEV_MODE="0",
        # Need to set these manually when in non-dev-mode
        SIREPO_COOKIE_IS_SECURE="0",
        SIREPO_COOKIE_PRIVATE_KEY="MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=",
        SIREPO_SMTP_PASSWORD="dev",
        SIREPO_SMTP_SERVER="dev",
        SIREPO_SMTP_USER="dev",
    )


def test_parse_python_errors():
    from sirepo.pkcli import job_cmd
    from pykern.pkunit import pkeq

    err = """
Traceback (most recent call last):
  File "/home/vagrant/src/radiasoft/sirepo/sirepo/pkcli/zgoubi.py", line 120, in _validate_estimate_output_file_size
    'Estimated FAI output too large.\n'
AssertionError: Estimated FAI output too large.
Reduce particle count or number of runs,
or increase diagnostic interval.
"""
    pkeq(
        job_cmd._parse_python_errors(err),
        """Estimated FAI output too large.
Reduce particle count or number of runs,
or increase diagnostic interval.""",
    )


def test_runError(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    import time

    d = fc.sr_sim_data()
    d.models.simulation.name = "srunit_error_run"
    d = fc.sr_post(
        "runSimulation",
        dict(
            forceRun=False,
            models=d.models,
            report="heightWeightReport",
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    for _ in range(fc.timeout_secs()):
        if d.state == "error":
            pkunit.pkeq("a big ugly error", d.error)
            return
        time.sleep(1)
        d = fc.sr_post("runStatus", d.nextRequest)
    else:
        pkunit.pkfail("Error never returned d={}", d)
