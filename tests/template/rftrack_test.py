# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.rftrack`

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# TODO(pjm): reenable tests after container beamsim is built with new rftrack location


def xtest_analytic_cavity_gain():
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


def xtest_aperture_shapes():
    """A particle beyond an element's aperture is lost: circular is an
    ellipse with half-axes X and Y, rectangular a rectangle, none no
    aperture, in a Lattice and a Volume."""
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    # x, y [mm] -> survives with none, circular, rectangular
    expect = {
        (8.0, 0.0): (1, 1, 1),
        (8.0, 4.0): (1, 0, 1),
        (12.0, 0.0): (1, 0, 0),
    }
    for element_position in ("relative", "absolute"):
        for i, shape in enumerate(("none", "circular", "rectangular")):
            m, b = _beamline(
                PKDict(
                    type="DRIFT",
                    l=0.1,
                    apertureShape=shape,
                    aperture_x=0.01,
                    aperture_y=0.005,
                ),
                element_position,
            )
            for (x, y), e in expect.items():
                p = _particle(m, x=x, y=y)
                if element_position == "absolute":
                    p = m.rft.Bunch6dT(p)
                pkunit.pkeq(
                    e[i],
                    b.track(p).get_ngood(),
                    "{} {} x={} y={}",
                    element_position,
                    shape,
                    x,
                    y,
                )


def xtest_bpm_resolution():
    """A BPM's readings have its resolution's random error, the same for
    the same seed."""
    import numpy
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    def _readings(resolution):
        m, b = _beamline(PKDict(type="BPM", l=0.05, resolution=resolution), "relative")
        e = b.get_elements_by_name("E1")
        pkunit.pkeq(resolution, e.get_resolution())
        m.rft.rng_set_seed(1)
        b.track(_particle(m, x=1.0))
        return numpy.array([b.get_bpms()[0].get_reading()[:2] for _ in range(3)])

    numpy.testing.assert_allclose(_readings(0.0), [[1.0, 0.0]] * 3, atol=1e-9)
    r = _readings(0.5)
    pkunit.pkok(numpy.std(r[:, 0]) > 0.05, "no reading error={}", r)
    numpy.testing.assert_array_equal(r, _readings(0.5))


def xtest_coil():
    """A COIL is a current loop in the middle of L: its on-axis field
    falls as R^3 / (R^2 + dz^2)^(3/2), and it focuses a particle at r by
    r'/r = -integral (Bz / (2 Brho))^2 dz, as a thin lens, in a Lattice and
    a Volume."""
    import numpy
    import scipy.constants
    from pykern.pkcollections import PKDict

    l = 0.5
    b0 = 0.5
    r = 0.05
    m, b = _beamline(PKDict(type="COIL", l=l, b_field=b0, radius=r), "relative")
    dz = numpy.array([0.0, r, 2 * r])
    numpy.testing.assert_allclose(
        [
            b.get_elements_by_name("E1").get_field(0, 0, (l / 2 + z) * 1e3, 0)[1][2]
            for z in dz
        ],
        b0 * r**3 / (r**2 + dz**2) ** 1.5,
        rtol=1e-12,
    )
    # integral over |dz| < l / 2 of (R^2 / (R^2 + dz^2))^3 = R F(l / (2 R))
    u = l / (2 * r)
    f = 2 * (
        u / (4 * (1 + u**2) ** 2) + 3 * u / (8 * (1 + u**2)) + 3 / 8 * numpy.arctan(u)
    )
    brho = m.BUNCH.pc_mev * 1e6 / scipy.constants.c
    expect = -(b0**2) * r * f / (4 * brho**2)
    p = b.track(_particle(m, x=1.0)).get_phase_space("%x %xp %y %yp")[0]
    # 2e-2: the particle moves inward 1% in the coil
    numpy.testing.assert_allclose(
        (p[0] * p[1] + p[2] * p[3]) / (p[0] ** 2 + p[2] ** 2), expect, rtol=2e-2
    )
    m, b = _beamline(PKDict(type="COIL", l=l, b_field=b0, radius=r), "absolute")
    p = b.track(m.rft.Bunch6dT(_particle(m, x=1.0))).get_phase_space(
        "%X %Px %Y %Py %Pz"
    )[0]
    # X, Y [mm]
    numpy.testing.assert_allclose(
        (p[0] * p[1] + p[2] * p[3]) / p[4] / (p[0] ** 2 + p[2] ** 2) * 1e3,
        expect,
        rtol=2e-2,
    )


def xtest_fixup_recorded_autophase():
    """A simulation saved with Recorded t0 autophases again, and its
    elements' t0 is gone."""
    from pykern import pkunit
    from sirepo import simulation_db

    data = _shipped_example("X-band Linac FODO Cell")
    data.models.simulationSettings.autophase = "0"
    data.models.simulationSettings.autophaseReference = "recorded"
    for e in data.models.elements:
        if e.type == "CAVITY":
            e.t0 = 12.5
    data = simulation_db.fixup_old_data(data, force=True)[0]
    s = data.models.simulationSettings
    pkunit.pkeq("1", s.autophase)
    pkunit.pkeq("design", s.autophaseReference)
    pkunit.pkok(
        not any("t0" in e for e in data.models.elements), "an element kept its t0"
    )


def xtest_fixup_set_aperture():
    """A simulation saved with the Set Aperture checkbox has a circular
    aperture where it was checked, and none elsewhere."""
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    data = _example_data(
        elements=[
            PKDict(_id=2, type="DRIFT", name="D1", l=1.0, setAperture="1"),
            PKDict(_id=3, type="DRIFT", name="D2", l=1.0, setAperture="0"),
        ],
    )
    pkunit.pkeq(
        [("circular", False), ("none", False)],
        [(e.apertureShape, "setAperture" in e) for e in data.models.elements],
    )


def xtest_fixup_solenoid_radius():
    """A simulation saved before SOLENOID had a radius has its aperture_x,
    which was its bore radius."""
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    data = _example_data(
        elements=[
            PKDict(_id=2, type="SOLENOID", name="S1", l=0.2, aperture_x=0.02),
            PKDict(
                _id=3, type="SOLENOID", name="S2", l=0.2, aperture_x=0.02, radius=0.05
            ),
        ],
    )
    pkunit.pkeq([0.02, 0.05], [e.radius for e in data.models.elements])


def xtest_generate_python():
    from pykern import pkunit
    from sirepo.template import rftrack
    import re

    with pkunit.save_chdir_work():
        for name, expect in (
            ("AWA Zone #1", "awa-zone-1.py"),
            ("AWA Zone #2", "awa-zone-2.py"),
            ("CERN Linac4 CCDTL", "cern-linac4-ccdtl.py"),
            ("Corrector Steering Line", "corrector-steering-line.py"),
            ("X-band Linac FODO Cell", "x-band-linac-fodo-cell.py"),
        ):
            data = _shipped_example(name)
            data.report = "animation"
            pkunit.file_eq(
                expect,
                # the script's thread count is SIREPO_MPI_CORES, which differs
                # between machines (test.sh sets 2)
                actual=re.sub(
                    r"(num_threads=)\d+",
                    r"\g<1>1",
                    rftrack.python_source_for_model(data, model=None, qcall=None),
                ),
            )


def xtest_import_refused():
    """An archive with an element this app can't reproduce -- a static
    field, or a field map cropped by z0/z1 -- is refused, with every
    reason, before any lib file is written."""
    import numpy
    import RF_Track as rft
    import lume_rftrack.archive
    import sirepo.util
    from lume_rftrack.simulator import RFTrackSimulator
    from pykern import pkunit
    from sirepo.template import rftrack

    d = rft.Drift(0.5)
    d.set_name("D1")
    d.set_static_Bfield(0.0, 0.01, 0.0)
    z = numpy.linspace(0.0, 0.1, 41)
    s = rft.Static_Magnetic_FieldMap_1d(numpy.full(len(z), 0.1), z[1] - z[0])
    s.set_name("S1")
    s.set_z1(0.05)
    lattice = rft.Lattice()
    lattice.append(d)
    lattice.append(s)
    a = str(pkunit.empty_work_dir().join("a.h5"))
    RFTrackSimulator(
        lattice,
        rft.Bunch6d(rft.electronmass, 1.0, -1.0, numpy.array([0, 0, 0, 0, 0, 10.0])),
    ).archive(a)
    try:
        rftrack.build_imported_data(
            lume_rftrack.archive.read_archive(a), "a", qcall=None
        )
    except sirepo.util.UserAlert as e:
        for x in (
            r"'D1' \(Drift\) has a static_Bfield",
            r"'S1' \(Static_Magnetic_FieldMap_1d\) uses only",
        ):
            pkunit.pkre(x, e.sr_args.error)
        return
    pkunit.pkfail("expected a UserAlert")


def xtest_import_round_trip(monkeypatch):
    """Each import_file_test archive, imported and tracked by the generated
    script, tracks like lume_rftrack's own reload of it: exactly for the
    Volume; for the Lattice, whose cavities the script phases again from
    the bunch rather than restoring their archived t0, to 1e-6 in Pz and
    2e-3 of a standard deviation otherwise."""
    import subprocess
    import sys
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict

    d = pkunit.data_dir().dirpath().join("import_file_data")
    with pkunit.save_chdir_work():
        import lume_rftrack.archive
        import lume_rftrack.utils
        import numpy
        import sirepo.sim_data
        from lume_rftrack.simulator import RFTrackSimulator
        from sirepo.template import rftrack

        # the generated script reads lib files from the current directory
        monkeypatch.setattr(
            rftrack,
            "_write_lib_file_once",
            lambda full_name, content, alert, qcall: pkio.py_path(full_name).write(
                content, mode="wb" if isinstance(content, bytes) else "w"
            ),
        )
        c = lume_rftrack.utils.PHASE_SPACE_COLUMNS
        for case, tolerance in (
            ("fieldmap", PKDict(pz=1e-6, std=2e-3)),
            ("volume", PKDict(pz=1e-12, std=1e-9)),
        ):
            a = str(d.join(f"rftrack-{case}.in", "archive.h5"))
            data = rftrack.build_imported_data(
                lume_rftrack.archive.read_archive(a), "archive", qcall=None
            )
            sirepo.sim_data.get_class("rftrack").fixup_old_data(data, qcall=None)
            data.report = "animation"
            pkio.write_text(
                "parameters.py",
                rftrack.python_source_for_model(data, model=None, qcall=None),
            )
            subprocess.check_call(
                [sys.executable, "parameters.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            actual = numpy.load(rftrack._FINAL_PARTICLES_FILE)
            s = RFTrackSimulator()
            s.load_archive(a)
            if s.space_charge:
                s.apply_space_charge()
            s.track()
            lume_rftrack.utils.save_particles("expect.npy", s.tracked_bunch)
            expect = numpy.load("expect.npy")
            numpy.testing.assert_allclose(
                actual[:, c.index("Pz")].mean(),
                expect[:, c.index("Pz")].mean(),
                rtol=tolerance.pz,
                err_msg=case,
            )
            for k in ("x", "y", "Px", "Py", "Pz"):
                a_k = actual[:, c.index(k)]
                e_k = expect[:, c.index(k)]
                numpy.testing.assert_allclose(
                    [a_k.mean(), a_k.std()],
                    [e_k.mean(), e_k.std()],
                    rtol=tolerance.std,
                    atol=tolerance.std * e_k.std(),
                    err_msg=f"{case} {k}",
                )


def xtest_lattice_integration():
    """A Lattice element gets its step counts and, if it integrates its
    field, its integrator; 0 steps keeps RF-Track's default."""
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    _, b = _beamline(
        PKDict(
            type="SEXTUPOLE",
            l=0.1,
            nsteps=7,
            ttNsteps=5,
            scNsteps=3,
            odeintAlgorithm="rk4",
            odeintEpsabs=1e-6,
            odeintEpsrel=1e-5,
        ),
        "relative",
    )
    e = b.get_elements_by_name("E1")
    pkunit.pkeq(
        (7, 5, 3, "rk4", 1e-6, 1e-5),
        (
            e.get_nsteps(),
            e.get_tt_nsteps(),
            e.get_sc_nsteps(),
            e.get_odeint_algorithm(),
            e.get_odeint_epsabs(),
            e.get_odeint_epsrel(),
        ),
    )
    _, b = _beamline(PKDict(type="CORRECTOR", l=0.02), "relative")
    pkunit.pkeq(10, b.get_elements_by_name("E1").get_nsteps())
    # a transfer matrix, with no integrator
    _, b = _beamline(PKDict(type="QUADRUPOLE", l=0.1, nsteps=3), "relative")
    pkunit.pkeq(3, b.get_elements_by_name("E1").get_nsteps())


def xtest_lattice_misalignment():
    """A Lattice element's misalignment is a position offset in meters and
    rotations in radians about x (pitch), y (yaw) and z (roll): an offset
    quadrupole kicks a particle on axis by about K1 L dx, and tilting it
    about x kicks in y, about y kicks in x."""
    import numpy
    import scipy.constants
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo.template import rftrack

    data = _shipped_example("X-band Linac FODO Cell")
    data.report = "animation"
    s = rftrack.python_source_for_model(data, model=None, qcall=None)
    m = PKDict()
    exec(s[: -len("main()\n")], m)
    rft = m.rft
    rft.cvar.number_of_threads = 1
    quad = next(e for e in m.ELEMENTS if e.kind == "quadrupole_gradient")
    pc = m.BUNCH.pc_mev
    kl = quad.gradient * quad.l / (pc * 1e6 / scipy.constants.c)

    def _kick(**misalignment):
        m.ELEMENTS = [
            PKDict(
                {
                    **quad,
                    **{"dx": 0, "dy": 0, "dz": 0, "rx": 0, "ry": 0, "rz": 0},
                    **misalignment,
                }
            )
        ]
        b = rft.Bunch6d(
            m.BUNCH.mass_mev,
            0.0,
            m.BUNCH.charge,
            numpy.array([0.0, 0.0, 0.0, 0.0, 0.0, pc]),
        )
        return numpy.abs(m.build_beamline().track(b).get_phase_space("%xp %yp")[0])

    # 5%: the quadrupole is thick; xp, yp are in mrad, dx in mm
    numpy.testing.assert_allclose(_kick(dx=1e-3)[0], kl * 1.0, rtol=0.05)
    x, y = _kick(rx=0.01)
    pkunit.pkok(y > 10 * x, "rx should kick in y: xp={} yp={}", x, y)
    x, y = _kick(ry=0.01)
    pkunit.pkok(x > 10 * y, "ry should kick in x: xp={} yp={}", x, y)


def xtest_lattice_space_charge():
    """A Lattice applies space charge only with kicks: the Total
    Space-Charge Kicks spread over the elements, or, with 0, the
    elements' own."""
    import subprocess
    import sys
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict

    with pkunit.save_chdir_work():
        import lume_rftrack.utils
        import numpy
        from sirepo.template import rftrack

        def _sigma_x(space_charge, total, element):
            data = _example_data(
                elements=[
                    PKDict(_id=2, type="DRIFT", name="D1", l=2.0, scNsteps=element)
                ],
                beam=PKDict(pc=5.0, charge_nC=10.0, np=2000, sigma_pt=0.1),
                simulation_settings=PKDict(
                    spaceCharge=space_charge, scLatticeNsteps=total
                ),
            )
            data.models.simulation.elementPosition = "relative"
            pkio.write_text(
                "parameters.py",
                rftrack.python_source_for_model(data, model=None, qcall=None),
            )
            subprocess.check_call(
                [sys.executable, "parameters.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return numpy.load(rftrack._FINAL_PARTICLES_FILE)[
                :, lume_rftrack.utils.PHASE_SPACE_COLUMNS.index("x")
            ].std()

        none = _sigma_x("none", 100, 0)
        for total, element, grows in ((100, 0, True), (0, 0, False), (0, 10, True)):
            r = _sigma_x("pic", total, element) / none
            pkunit.pkeq(
                grows,
                r > 2,
                "total={} element={} sigma_x ratio={}",
                total,
                element,
                r,
            )


def xtest_rpn_undefined_variable():
    from pykern import pkunit
    from sirepo.template import rftrack
    import sirepo.util

    data = _shipped_example("X-band Linac FODO Cell")
    data.report = "animation"
    q = next(e for e in data.models.elements if e.type == "QUADRUPOLE")
    q.gradient = "nope * 2"
    try:
        rftrack.python_source_for_model(data, model=None, qcall=None)
    except sirepo.util.UserAlert as e:
        pkunit.pkre(q.name + " gradient", e.sr_args.error)
        return
    pkunit.pkfail("expected a UserAlert for an undefined variable")


def xtest_rpn_variables():
    """Variables in element, beam and beamline position fields generate the
    same script as the values they evaluate to."""
    import copy
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo.template import rftrack

    data = _shipped_example("X-band Linac FODO Cell")
    data.report = "animation"
    expect = rftrack.python_source_for_model(data, model=None, qcall=None)
    d = copy.deepcopy(data)
    dm = d.models
    pc = dm.beam.pc
    q = next(e for e in dm.elements if e.type == "QUADRUPOLE")
    b = dm.beamlines[0]
    i = next(i for i, p in enumerate(b.positions) if p.elemedge)
    dm.rpnVariables = [
        PKDict(name="half_pc", value=pc / 2),
        PKDict(name="half_gradient", value=q.gradient / 2),
        PKDict(name="z0", value=b.positions[i].elemedge / 2),
        PKDict(name="pc2", value="half_pc * 2"),
    ]
    dm.beam.pc = "pc2"
    q.gradient = "2 * half_gradient"
    b.positions[i].elemedge = "z0 * 2"
    pkunit.pkeq(expect, rftrack.python_source_for_model(d, model=None, qcall=None))
    pkunit.pkeq(
        pc,
        rftrack.prepare_for_client(d, None).models.rpnCache["pc2"],
    )


def xtest_sbend():
    """A sector SBEND in a Lattice keeps an on-momentum particle on axis
    and moves one with momentum error d by the dispersion rho (1 - cos
    angle) d, x' sin(angle) d, and its edge focusing uses its hgap and
    fint. A Volume, which places every element on one straight axis,
    refuses an SBEND or RBEND."""
    import numpy
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.util

    l = 0.5
    angle = 0.1
    d = 1e-3
    sbend = PKDict(type="SBEND", l=l, angle=angle)
    m, b = _beamline(sbend, "relative")
    pc = m.BUNCH.pc_mev
    numpy.testing.assert_allclose(
        b.track(_particle(m)).get_phase_space("%x %xp")[0], [0, 0], atol=1e-9
    )
    # x [mm], x' [mrad]; 2e-3: second order in d
    numpy.testing.assert_allclose(
        b.track(_particle(m, pc=pc * (1 + d))).get_phase_space("%x %xp")[0],
        numpy.array([l / angle * (1 - numpy.cos(angle)), numpy.sin(angle)]) * d * 1e3,
        rtol=2e-3,
    )
    edges = PKDict(e1=angle / 2, e2=angle / 2)
    m, b = _beamline(PKDict(sbend, hgap=0.02, fint=0.5, **edges), "relative")
    e = m.rft.SBend(l, angle, pc / m.BUNCH.charge, edges.e1, edges.e2)
    e.set_hgap(0.02)
    e.set_fint(0.5)
    direct = m.rft.Lattice()
    direct.append(e)
    yp = b.track(_particle(m, y=1.0)).get_phase_space("%yp")[0, 0]
    numpy.testing.assert_allclose(
        yp,
        direct.track(_particle(m, y=1.0)).get_phase_space("%yp")[0, 0],
        rtol=1e-12,
    )
    _, hard_edge = _beamline(PKDict(sbend, **edges), "relative")
    hard_edge_yp = hard_edge.track(_particle(m, y=1.0)).get_phase_space("%yp")
    # the fringe field reduces the vertical edge focusing
    numpy.testing.assert_array_less(abs(yp) * 1.05, abs(hard_edge_yp[0, 0]))
    for t in ("RBEND", "SBEND"):
        with pkunit.pkexcept(sirepo.util.UserAlert):
            _beamline(PKDict(sbend, type=t), "absolute")


def xtest_screen_size():
    """A screen records only the particles within its width and height,
    or all of them with 0, in a Lattice and a Volume."""
    import numpy
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    for element_position in ("relative", "absolute"):
        for size, expect in ((0.004, 1), (0.0, 2)):
            m, b = _beamline(
                [
                    PKDict(type="DRIFT", l=0.1),
                    PKDict(type="SCREEN", width=size, height=size),
                ],
                element_position,
            )
            p = m.rft.Bunch6d(
                m.BUNCH.mass_mev,
                1.0,
                m.BUNCH.charge,
                numpy.array(
                    [[x, 0.0, 0.0, 0.0, 0.0, m.BUNCH.pc_mev] for x in (1.0, 3.0)]
                ),
            )
            if element_position == "absolute":
                p = m.rft.Bunch6dT(p)
            b.track(p)
            pkunit.pkeq(
                expect,
                len(b.get_elements_by_name("E2").get_bunch().get_phase_space("%x")),
                "{} size={}",
                element_position,
                size,
            )


def xtest_sextupole():
    """A SEXTUPOLE kicks a particle at (x, y) by x' = -k2 L (x^2 - y^2) / 2,
    y' = k2 L x y, as MAD-X defines k2, in a Lattice and a Volume; a
    Field Gradient strength is k2 times the beam's (signed) rigidity."""
    import numpy
    import scipy.constants
    from pykern.pkcollections import PKDict

    l = 0.1
    k2 = 50.0
    # x, y [mm]
    x = numpy.array([1.0, 0.0, 1.0])
    y = numpy.array([0.0, 1.0, 1.0])
    # x', y' [mrad]; thin lens, which this thick sextupole is to 1e-3
    expect = numpy.array([-k2 * l * (x**2 - y**2) / 2, k2 * l * x * y]).T * 1e-3
    for strength in (
        PKDict(strengthType="k2", k2=k2),
        PKDict(strengthType="gradient"),
    ):
        for element_position in ("relative", "absolute"):
            sextupole = PKDict(type="SEXTUPOLE", l=l, **strength)
            if strength.strengthType == "gradient":
                m, _ = _beamline(PKDict(type="DRIFT", l=l), element_position)
                sextupole.gradient = (
                    k2 * m.BUNCH.pc_mev / m.BUNCH.charge * 1e6 / scipy.constants.c
                )
            m, b = _beamline(sextupole, element_position)
            if element_position == "relative":
                actual = [
                    b.track(_particle(m, x=x[i], y=y[i])).get_phase_space("%xp %yp")[0]
                    for i in range(len(x))
                ]
            else:
                actual = []
                for i in range(len(x)):
                    p = b.track(
                        m.rft.Bunch6dT(_particle(m, x=x[i], y=y[i]))
                    ).get_phase_space("%Px %Py %Pz")[0]
                    actual.append(p[:2] / p[2] * 1e3)
            numpy.testing.assert_allclose(
                actual,
                expect,
                rtol=1e-3,
                atol=1e-3 * numpy.abs(expect).max(),
                err_msg=f"{strength.strengthType} {element_position}",
            )


def xtest_solenoid():
    """An analytic SOLENOID's on-axis field at its centre is
    B0 L / sqrt(L^2 + 4 R^2) for its bore radius R, whatever its
    aperture."""
    import numpy
    from pykern.pkcollections import PKDict

    l = 0.2
    b0 = 0.1
    r = 0.05
    _, b = _beamline(
        PKDict(
            type="SOLENOID",
            l=l,
            b_field=b0,
            radius=r,
            apertureShape="circular",
            aperture_x=0.01,
            aperture_y=0.01,
        ),
        "relative",
    )
    numpy.testing.assert_allclose(
        b.get_elements_by_name("E1").get_field(0, 0, l / 2 * 1e3, 0)[1][2],
        b0 * l / numpy.sqrt(l**2 + 4 * r**2),
        rtol=1e-12,
    )


def xtest_stat_plot_presets():
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


def xtest_track_drift_and_screen():
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
        import lume_rftrack.utils

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
            p[:, lume_rftrack.utils.PHASE_SPACE_COLUMNS.index("weight")].sum(),
            data.models.beam.charge_nC * 1e-9,
            rtol=1e-6,
        )
        res = rftrack.background_percent_complete("animation", pkio.py_path("."), True)
        pkunit.pkok(
            res.percentComplete > 90, "percentComplete={} too low", res.percentComplete
        )


def xtest_volume_settings():
    """A Volume gets its integration algorithm, error tolerances and
    maximum tracking time, which stops a particle short of the tracking
    end; 0 is no limit."""
    import numpy
    from pykern import pkunit
    from pykern.pkcollections import PKDict

    drift = PKDict(type="DRIFT", l=1.0)
    m, b = _beamline(
        drift,
        "absolute",
        PKDict(
            odeintAlgorithm="rk8pd",
            odeintEpsabs=1e-6,
            odeintEpsrel=1e-4,
            volumeTMaxMm=500.0,
        ),
    )
    pkunit.pkeq(
        ("rk8pd", 1e-6, 1e-4, 500.0),
        (b.odeint_algorithm, b.odeint_epsabs, b.odeint_epsrel, b.t_max_mm),
    )
    # Z [mm]: v is nearly c
    numpy.testing.assert_allclose(
        b.track(m.rft.Bunch6dT(_particle(m))).get_phase_space("%Z")[0, 0],
        500.0,
        rtol=1e-3,
    )
    _, b = _beamline(drift, "absolute")
    pkunit.pkeq(numpy.inf, b.t_max_mm)


def _beamline(element, element_position, simulation_settings=None):
    """`element` (an element model, without `_id` or `name`, or a list of
    them, named E1, E2, ...) alone in a beamline positioned by
    `element_position`, with `simulation_settings`, built by the generated
    script: returns the script's namespace and the beamline"""
    from pykern.pkcollections import PKDict
    from sirepo.template import rftrack

    data = _example_data(
        elements=[
            PKDict(_id=i + 2, name=f"E{i + 1}", **e)
            for i, e in enumerate(element if isinstance(element, list) else [element])
        ],
        simulation_settings=simulation_settings,
    )
    data.models.simulation.elementPosition = element_position
    res = PKDict()
    exec(
        rftrack.python_source_for_model(data, model=None, qcall=None)[
            : -len("main()\n")
        ],
        res,
    )
    res.rft.cvar.number_of_threads = 1
    return res, res.build_beamline()


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


def _particle(m, pc=None, x=0.0, y=0.0):
    """One particle of the beam `m` (a generated script's namespace) at
    (`x`, `y`) [mm], with momentum `pc` [MeV/c], the beam's by default"""
    import numpy

    return m.rft.Bunch6d(
        m.BUNCH.mass_mev,
        0.0,
        m.BUNCH.charge,
        numpy.array([x, 0.0, y, 0.0, 0.0, m.BUNCH.pc_mev if pc is None else pc]),
    )


def _shipped_example(name):
    from sirepo import simulation_db
    from sirepo.template import rftrack

    for d in simulation_db.examples(rftrack.SIM_TYPE):
        if d.models.simulation.name == name:
            return simulation_db.fixup_old_data(d)[0]
    raise AssertionError(f"no example named {name!r}")
