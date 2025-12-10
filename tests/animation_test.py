"""Test background processes

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict


def test_controls(fc):
    fc.sr_animation_run(
        fc.sr_sim_data("FODO with instruments"),
        "instrumentAnimation",
        PKDict(),
        expect_completed=False,
    )


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


def test_jspec(fc):
    data = fc.sr_sim_data("DC Cooling Example")
    data.models.simulationSettings.update(
        PKDict(
            time=1,
            step_number=1,
            time_step=1,
        )
    )
    fc.sr_animation_run(
        data,
        "animation",
        PKDict(
            # TODO(robnagler) these are sometimes off, just rerun
            beamEvolutionAnimation=PKDict(
                frame_index=0,
                expect_y_range=r"2.15e-06",
            ),
            coolingRatesAnimation=PKDict(
                frame_index=0,
                expect_x_range=r"0, 1\.0",
            ),
        ),
        timeout=20,
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


def test_activait(fc):
    fc.sr_animation_run(
        fc.sr_sim_data("iris Dataset"),
        "animation",
        PKDict(),
        timeout=45,
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


def test_hellweg(fc):
    fc.sr_animation_run(
        fc.sr_sim_data("RF Fields"),
        "beamAnimation",
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


def test_zgoubi(fc):
    fc.sr_animation_run(
        fc.sr_sim_data("EMMA"),
        "animation",
        PKDict(
            bunchAnimation=PKDict(
                expect_title=lambda i: (
                    "Pass {}".format(i) if i else "Initial Distribution"
                ),
                expect_y_range=lambda i: [
                    "-0.0462.*, -0.0281.*, 200",
                    "-0.0471.*, -0.0283.*, 200",
                    "-0.0472.*, -0.0274.*, 200",
                    "-0.0460.*, -0.0280.*, 200",
                    "-0.0460.*, -0.0294.*, 200",
                    "-0.0473.*, -0.0275.*, 200",
                    "-0.0480.*, -0.0281.*, 200",
                    "-0.0479.*, -0.0299.*, 200",
                    "-0.0481.*, -0.0294.*, 200",
                    "-0.0488.*, -0.0292.*, 200",
                    "-0.0484.*, -0.0303.*, 200",
                ][i],
            ),
        ),
    )
