"""test RF-Track's MAD-X lattice export

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_lattice_export(fc):
    from pykern import pkcompat, pkunit
    from pykern.pkcollections import PKDict

    d = fc.sr_sim_data("IOTA Ring")
    r = fc.sr_get(
        "pythonSource",
        PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            # the settings menu's "Export as MAD-X lattice"
            model="madx",
        ),
    )
    t = pkcompat.from_bytes(r.data)
    pkunit.pkre(r"beam,.*particle=electron", t)
    pkunit.pkre(r"M1L: SBEND,angle=0\.5235987756", t)
    pkunit.pkre(r"\nuse,sequence=", t)
