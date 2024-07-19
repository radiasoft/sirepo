"""Test openmc

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict

_SIM_TYPE = "openmc"


def test_stp_file(fc):
    from pykern import pkunit

    fc.sr_get_root(sim_type=_SIM_TYPE)
    d = fc.sr_post(
        "newSimulation",
        PKDict(
            simulationType=fc.sr_sim_type,
            folder="/",
            name="custom_stp",
        ),
    )
    fc.sr_post_form(
        "uploadLibFile",
        params=PKDict(
            simulation_type=_SIM_TYPE,
            simulation_id=d.models.simulation.simulationId,
            file_type="geometryInput-dagmcFile",
        ),
        data=PKDict(),
        file=pkunit.data_dir().join("box.stp"),
    )
    d.models.geometryInput.dagmcFile = "box.stp"
    r = fc.sr_run_sim(
        data=fc.sr_post("saveSimulationData", d),
        model="dagmcAnimation",
    )
    pkunit.pkok("completed", r.state)
