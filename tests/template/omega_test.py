"""omega new simulation tests

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
import pytest

_SIM_TYPE = "omega"

pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        sim_types="elegant:omega:opal",
    ),
)


def test_opal_elegant(fc):
    from pykern import pkunit

    fc.sr_get_root(sim_type=_SIM_TYPE)
    r = fc.sr_post(
        "newSimulation",
        PKDict(
            simulationType=fc.sr_sim_type,
            folder="/",
            name="opal_elegant",
        ),
    )
    r.models.simWorkflow = PKDict(
        coupledSims=[
            _coupled_sim(fc, "opal", "CSR Bend Drift"),
            _coupled_sim(fc, "elegant", "bunchComp - fourDipoleCSR"),
        ],
    )
    r = fc.sr_run_sim(
        data=fc.sr_post("saveSimulationData", r),
        model="animation",
    )
    pkunit.pkok("completed", r.state)


def _coupled_sim(fc, stype, sname):
    r = fc.sr_sim_data(sim_type=stype, sim_name=sname)
    fc.sr_sim_type_set(_SIM_TYPE)
    return PKDict(
        simulationId=r.models.simulation.simulationId,
        simulationType=stype,
    )
