"""Test "Open as a New ... Simulation" between elegant, MAD-X, OPAL and
RF-Track

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest

# the codes converted between, whichever the environment enables, and the
# test client's default (myapp)
pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(sim_types="elegant:madx:myapp:opal:rftrack"),
)


def test_convert_lattice(fc):
    from pykern import pkunit
    from sirepo import feature_config

    e = _examples()
    for from_type, name in e.items():
        targets = sorted(t for t in e if t != from_type)
        pkunit.pkeq(
            targets,
            feature_config.for_sim_type(from_type).lattice_conversion_targets,
        )
        d = fc.sr_sim_data(sim_name=name, sim_type=from_type)
        for to_type in targets:
            _convert(fc, d, from_type, to_type)


def test_rf_field_map(fc):
    from pykern import pkcompat
    from pykern import pkunit

    d = _convert(
        fc,
        fc.sr_sim_data(sim_name="bunchComp - fourDipoleCSR", sim_type="elegant"),
        "elegant",
        "opal",
    )
    f = "madx-rfcavity-0.3m-2856MHz.txt"
    pkunit.pkok(
        any(e.type == "RFCAVITY" and e.fmapfn == f for e in d.models.elements),
        "no RFCAVITY with fmapfn={}",
        f,
    )
    # written by the agent
    r = fc.sr_get(
        "downloadLibFile",
        params=PKDict(
            simulation_type="opal",
            filename=f"RFCAVITY-fmapfn.{f}",
        ),
    )
    pkunit.pkre(r"^1DDynamic \d+\n0 30 \d+\n2856\n", pkcompat.from_bytes(r.data))


def _convert(fc, data, from_type, to_type):
    from pykern import pkunit

    # same requests as the simConversionModal directive
    r = fc.sr_post(
        "statefulCompute",
        PKDict(
            method="convert_lattice",
            models=data.models,
            args=PKDict(toSimType=to_type),
            simulationId=data.models.simulation.simulationId,
            simulationType=from_type,
        ),
    )
    c = r.imported_data
    pkunit.pkeq(to_type, c.simulationType)
    pkunit.pkeq(data.models.simulation.name, c.models.simulation.name)
    n = fc.sr_post(
        "newSimulation",
        PKDict(c.models.simulation).pkupdate(simulationType=to_type),
    )
    for f in ("simulationId", "simulationSerial"):
        c.models.simulation[f] = n.models.simulation[f]
    c.version = n.version
    res = fc.sr_post("saveSimulationData", c)
    pkunit.pkeq(to_type, res.simulationType)
    pkunit.pkok(
        res.models.elements and res.models.beamlines,
        "from={} to={} missing elements or beamlines",
        from_type,
        to_type,
    )
    return res


def _examples():
    """An example of each code converted"""
    return PKDict(
        elegant="SPEAR3",
        madx="FODO PTC",
        opal="CSR Bend Drift",
        rftrack="X-band Linac FODO Cell",
    )
