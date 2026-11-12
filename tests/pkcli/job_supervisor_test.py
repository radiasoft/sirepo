"""Test pkcli.job_supervisor

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_content_for_log():
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdc, pkdlog, pkdp
    from sirepo.pkcli import job_supervisor
    import sirepo.job

    c = PKDict({"api": "api_runSimulation", sirepo.job.SERVER_SECRET_KEY: "secret"})
    pkunit.pkeq(PKDict(api="api_runSimulation"), job_supervisor._content_for_log(c))
    # ServerReq.receive still needs the secret
    pkunit.pkeq("secret", c[sirepo.job.SERVER_SECRET_KEY])
    pkunit.pkeq("<unparsable>", job_supervisor._content_for_log(None))
    pkunit.pkeq("<unparsable>", job_supervisor._content_for_log("not parsed"))
