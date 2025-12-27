"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest


def test_elegant(fc):
    import sirepo.template.lattice

    data = fc.sr_sim_data("Compact Storage Ring")
    sirepo.template.lattice.LatticeUtil.find_first_command(
        data, "bunched_beam"
    ).n_particles_per_bunch = 1
    fc.sr_animation_run(
        data,
        "animation",
        PKDict(
            {
                "elementAnimation22-13": PKDict(
                    expect_x_range="0.0, 46",
                    expect_y_range="-1.*e-15, 34.6",
                ),
            }
        ),
        timeout=30,
    )


def test_madx(fc):
    import sirepo.template.lattice

    data = fc.sr_sim_data("FODO PTC")
    sirepo.template.lattice.LatticeUtil.find_first_command(data, "beam").npart = 1
    fc.sr_animation_run(
        data,
        "animation",
        PKDict(),
    )


def test_opal(fc):
    fc.sr_animation_run(
        fc.sr_sim_data("CSR Bend Drift"),
        "animation",
        PKDict(),
    )


def test_radia(fc):
    fc.sr_animation_run(
        fc.sr_sim_data("Parameterized C-Bend Dipole"),
        "solverAnimation",
        PKDict(),
    )


def test_srw(fc):
    data = fc.sr_sim_data("Young's Double Slit Experiment")
    data.models.multiElectronAnimation.pkupdate(
        numberOfMacroElectrons=4,
    )
    data.models.simulation.sampleFactor = 0.0001
    fc.sr_animation_run(
        data,
        "multiElectronAnimation",
        PKDict(
            multiElectronAnimation=PKDict(
                # Prevents "Memory Error" because SRW uses computeJobStart as frameCount
                frame_index=0,
                expect_title="Intensity at W60, 60 m \(E=4.24 keV\)",
            ),
        ),
        timeout=20,
    )
