"""test downloadDataFile

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_madx_log_download(fc):
    from pykern import pkunit, pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo.template import lattice

    d = fc.sr_sim_data("FODO PTC")
    lattice.LatticeUtil.find_first_command(d, "beam").npart = 1
    fc.sr_animation_run(d, "animation", PKDict())
    r = fc.sr_get(
        "downloadDataFile",
        PKDict(
            simulation_type=d.simulationType,
            simulation_id=d.models.simulation.simulationId,
            model="animation",
            frame="-1",
        ),
    )
    pkunit.pkre('title, "FODO PTC"', pkcompat.from_bytes(r.data))
