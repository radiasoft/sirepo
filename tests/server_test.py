# -*- coding: utf-8 -*-
"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import csv
import pytest
import re
import six
import time


def test_elegant_data_file(fc):
    from pykern import pkunit, pkcompat, pkio
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import sdds
    from sirepo import feature_config

    data = fc.sr_sim_data("bunchComp - fourDipoleCSR")
    run = fc.sr_post(
        "runSimulation",
        PKDict(
            forceRun=False,
            models=data.models,
            report="bunchReport1",
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
        ),
    )
    pkunit.pkeq("pending", run.state, "not pending, run={}", run)
    for _ in range(fc.DEFAULT_TIMEOUT_SECS):
        if run.state == "completed":
            break
        time.sleep(1)
        run = fc.sr_post("runStatus", run.nextRequest)
    else:
        if run.state != "completed":
            pkunit.pkfail("runStatus: failed to complete: {}", run)
    r = fc.sr_get(
        "downloadDataFile",
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model="bunchReport1",
            frame="-1",
            suffix="csv",
        ),
    )
    pkunit.pkeq(200, r.status_code)
    pkunit.pkre("no-cache", r.header_get("Cache-Control"))
    # 50,000 particles plus header row
    pkunit.pkeq(50001, len(list(csv.reader(six.StringIO(pkcompat.from_bytes(r.data))))))
    r = fc.sr_get(
        "downloadDataFile",
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model="bunchReport1",
            frame="-1",
        ),
    )
    pkunit.pkeq(200, r.status_code)
    d = pkunit.work_dir()
    m = re.search(
        r'attachment; filename="([^"]+)"',
        r.header_get("Content-Disposition"),
    )
    path = d.join(m.group(1))
    path.write_binary(r.data)
    pkunit.pkeq(1, sdds.sddsdata.InitializeInput(0, str(path)))
    pkunit.pkne(0, len(sdds.sddsdata.GetColumnNames(0)))
    sdds.sddsdata.Terminate(0)


def test_myapp_basic(fc):
    from pykern import pkunit, pkcompat
    from pykern.pkunit import pkok, pkeq

    r = fc.sr_get("/robots.txt")
    pkunit.pkre("elegant.*myapp.*srw", pkcompat.from_bytes(r.data))


def test_srw(fc):
    from pykern import pkio, pkcompat
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    import json

    r = fc.sr_get_root()
    pkre("<!DOCTYPE html", pkcompat.from_bytes(r.data))
    d = fc.sr_post("listSimulations", {"simulationType": fc.sr_sim_type})
    pkeq(
        404, fc.sr_get("/find-by-name-auth/srw/default/UndulatorRadiation").status_code
    )
    for sep in (" ", "%20", "+"):
        pkeq(
            200,
            fc.sr_get(
                "/find-by-name-auth/srw/default/Undulator{}Radiation".format(sep)
            ).status_code,
        )
