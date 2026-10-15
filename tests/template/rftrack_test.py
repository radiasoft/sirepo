# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.rftrack`

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_analytic_cavity_gain():
    """An analytic CAVITY is a standing wave of half-wavelength cells: on
    crest, an ultrarelativistic particle gains gradient * l / 2, however
    many cells it has."""
    import numpy
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo.template import rftrack

    data = _shipped_example("X-band Linac FODO Cell")
    data.report = "animation"
    s = rftrack.python_source_for_model(data, model=None, qcall=None)
    # without the last line, main(), which would run the simulation
    pkunit.pkok(s.endswith("\nmain()\n"), "generated source does not end with main()")
    m = PKDict()
    exec(s[: -len("main()\n")], m)
    rft = m.rft
    rft.cvar.number_of_threads = 1
    spec = next(e for e in m.ELEMENTS if e.kind == "cavity_analytic")
    half_wavelength = rft.clight / (2.0 * spec.frequency_hz)
    for n_cells in (1, round(spec.l / half_wavelength)):
        spec.l = n_cells * half_wavelength
        lattice = rft.Lattice()
        lattice.append(m._build_element(spec))
        b = rft.Bunch6d(
            m.BUNCH.mass_mev,
            0.0,
            m.BUNCH.charge,
            numpy.array([0.0, 0.0, 0.0, 0.0, 0.0, m.BUNCH.pc_mev]),
        )
        lattice.autophase(b)
        # measured within 5e-4 for 1 and 12 cells: the field map's sampling
        numpy.testing.assert_allclose(
            lattice.track(b).get_phase_space("%Pc")[0, 0] - m.BUNCH.pc_mev,
            spec.gradient_v_per_m * spec.l / 2e6,
            rtol=1e-3,
            err_msg=f"n_cells={n_cells}",
        )


def test_generate_python():
    from pykern import pkunit
    from sirepo.template import rftrack

    with pkunit.save_chdir_work():
        for name in ("AWA Zone 1", "X-band Linac FODO Cell"):
            data = _shipped_example(name)
            data.report = "animation"
            pkunit.file_eq(
                name.lower().replace(" ", "-") + ".py",
                actual=rftrack.python_source_for_model(data, model=None, qcall=None),
            )


def test_stat_plot_presets():
    """Every Plot Presets entry (schema `statPlotPresets`) is in the
    `StatPlotPreset` menu and plots only real stat columns."""
    from pykern import pkunit
    from sirepo.template import rftrack

    presets = rftrack.SCHEMA.constants.statPlotPresets
    pkunit.pkeq(
        sorted(k for k, _ in rftrack.SCHEMA.enum.StatPlotPreset if k),
        sorted(presets.keys()),
    )
    columns = set(rftrack.stat_columns())
    for name, preset in presets.items():
        for f in ("x", "y1", "y2", "y3", "y4", "y5"):
            pkunit.pkok(
                preset[f] in columns,
                "preset={} {}={} is not a stat column",
                name,
                f,
                preset[f],
            )


def test_track_drift_and_screen():
    """A real run of the generated script. Its own `v.verbosity = 1` prints
    RF_Track's native progress lines to `run.log`, which
    `background_percent_complete()` reads back: since `is_running=True`,
    the estimate stays strictly under 100, but a fully tracked drift of a
    100 MeV/c electron (ultrarelativistic, beta very close to 1, the one
    case that estimate's "t [mm/c] / tracking end [mm]" math is accurate
    for) should land close to it.
    """
    import subprocess
    import sys
    from pykern import pkio, pkunit

    with pkunit.save_chdir_work():
        from sirepo import simulation_db
        from sirepo.template import rftrack, template_common
        import numpy
        import rslume.rftrack_utils

        # the default automatic tracking range is exactly the 1 m drift
        data = _example_data()
        simulation_db.write_json(template_common.INPUT_BASE_NAME, data)
        pkio.write_text(
            "parameters.py",
            rftrack.python_source_for_model(data, model=None, qcall=None),
        )
        with open(template_common.RUN_LOG, "w") as f:
            subprocess.check_call(
                [sys.executable, "parameters.py"], stdout=f, stderr=subprocess.STDOUT
            )
        for f in (
            rftrack._INITIAL_PARTICLES_FILE,
            rftrack._STATS_FILE,
            rftrack._FINAL_PARTICLES_FILE,
            rftrack._SCREEN_FILE.format(0),
        ):
            pkunit.pkok(pkio.py_path(f).exists(), "missing {}", f)
        pkunit.pkok(len(numpy.load(rftrack._STATS_FILE)) > 0, "empty stats")
        p = numpy.load(rftrack._FINAL_PARTICLES_FILE)
        pkunit.pkeq(data.models.beam.np, len(p))
        # a drift loses no particles, so their charges add up to the beam's
        numpy.testing.assert_allclose(
            p[:, rslume.rftrack_utils.PHASE_SPACE_COLUMNS.index("weight")].sum(),
            data.models.beam.charge_nC * 1e-9,
            rtol=1e-6,
        )
        res = rftrack.background_percent_complete("animation", pkio.py_path("."), True)
        pkunit.pkok(
            res.percentComplete > 90, "percentComplete={} too low", res.percentComplete
        )


def _example_data(
    elements=None, beamline_items=None, beam=None, simulation_settings=None
):
    import sirepo.sim_data
    from pykern.pkcollections import PKDict

    els = elements or [
        PKDict(_id=2, type="DRIFT", name="D1", l=1.0),
        PKDict(_id=3, type="SCREEN", name="S1", l=0),
    ]
    items = beamline_items or [e._id for e in els]
    # beamline.positions[idx].elemedge is the absolute z position of
    # items[idx]; default to sequential (cumulative length) placement,
    # matching what the lattice editor's "absolute" positioning mode would
    # have computed for a simple non-overlapping lattice.
    by_id = {e._id: e for e in els}
    positions = []
    edge = 0.0
    for item_id in items:
        positions.append(PKDict(elemedge=edge))
        edge += by_id[abs(item_id)].get("l", 0)

    data = PKDict(
        report="animation",
        simulationType="rftrack",
        models=PKDict(
            beam=PKDict(
                # mass and charge come from the particle type
                particle="electron",
                pc=100.0,
                charge_nC=1.0,
                np=100,
                emit_x=1.0,
                emit_y=1.0,
                beta_x=1.0,
                beta_y=1.0,
                alpha_x=0.0,
                alpha_y=0.0,
                sigma_t=1.0,
                sigma_pt=1.0,
            ).pkupdate(beam or PKDict()),
            beamlines=[
                PKDict(id=1, name="BL1", items=items, positions=positions),
            ],
            commands=[],
            elements=els,
            simulation=PKDict(
                visualizationBeamlineId=1,
                elementPosition="absolute",
            ),
            simulationSettings=PKDict(
                spaceCharge="none",
            ).pkupdate(simulation_settings or PKDict()),
        ),
    )
    sirepo.sim_data.get_class("rftrack").fixup_old_data(data, qcall=None)
    return data


def _shipped_example(name):
    from sirepo import simulation_db
    from sirepo.template import rftrack

    for d in simulation_db.examples(rftrack.SIM_TYPE):
        if d.models.simulation.name == name:
            return simulation_db.fixup_old_data(d)[0]
    raise AssertionError(f"no example named {name!r}")
