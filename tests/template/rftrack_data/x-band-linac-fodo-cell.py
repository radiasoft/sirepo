#!/usr/bin/env python

from pykern.pkcollections import PKDict
import RF_Track as rft
import math
import numpy
import lume_rftrack.simulator
import lume_rftrack.utils

ELEMENTS = [
    PKDict(
        name='D0',
        elemedge=0.0,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='drift',
        l=0.05,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
    PKDict(
        name='C1',
        elemedge=0.05,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='cavity_analytic',
        l=0.15,
        frequency_hz=11994200000.0,
        gradient_v_per_m=80000000.0,
        phase_deg=0.0,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
    PKDict(
        name='C2',
        elemedge=0.2,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='cavity_analytic',
        l=0.15,
        frequency_hz=11994200000.0,
        gradient_v_per_m=80000000.0,
        phase_deg=0.0,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
    PKDict(
        name='QF',
        elemedge=0.35,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='quadrupole_gradient',
        l=0.1,
        gradient=5.0,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
    PKDict(
        name='C3',
        elemedge=0.45,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='cavity_analytic',
        l=0.15,
        frequency_hz=11994200000.0,
        gradient_v_per_m=80000000.0,
        phase_deg=0.0,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
    PKDict(
        name='C4',
        elemedge=0.6,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='cavity_analytic',
        l=0.15,
        frequency_hz=11994200000.0,
        gradient_v_per_m=80000000.0,
        phase_deg=0.0,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
    PKDict(
        name='QD',
        elemedge=0.75,
        aperture_shape='none',
        aperture_x=0.015,
        aperture_y=0.015,
        dx=0.0,
        dy=0.0,
        dz=0.0,
        rx=0.0,
        ry=0.0,
        rz=0.0,
        kind='quadrupole_gradient',
        l=0.1,
        gradient=-5.0,
        nsteps=0,
        tt_nsteps=20,
        sc_nsteps=0,
        odeint_algorithm='rk2',
        odeint_epsabs=0.001,
        odeint_epsrel=0.0,
    ),
]
BUNCH = PKDict(
    charge=-1.0,
    mass_mev=0.51099895069,
    pc_mev=100.0,
    random_seed=5489,
    alpha_x=0.0,
    alpha_y=0.0,
    beta_x=1.0,
    beta_y=1.0,
    charge_nc=0.05,
    disp_px=0.0,
    disp_py=0.0,
    disp_x=0.0,
    disp_y=0.0,
    emit_x=5.0,
    emit_y=5.0,
    np=10000,
    sigma_pt=1.0,
    sigma_t=1.0,
)
SETTINGS = PKDict(
    num_threads=1,
    space_charge=PKDict(
    ),
)


def autophase(volume, bunch):
    p0 = rft.Bunch6d(
        BUNCH.mass_mev, 0.0, BUNCH.charge, numpy.array([0.0, 0.0, 0.0, 0.0, 0.0, BUNCH.pc_mev])
    )
    volume.unset_t0()
    volume.autophase(p0)


def build_beamline():
    # Lattice appends elements sequentially with no absolute-position
    # concept at all -- gaps were already filled with synthetic Drifts
    # and overlaps rejected when ELEMENTS was generated, so every element
    # here simply begins where the previous one ended. There is no
    # Volume-style tracking range to set (a Lattice is inherently bounded
    # by its own appended elements), and no continuous-ODE step size to
    # tune (dt_mm/odeint_algorithm/tt_dt_mm are Volume-only) -- each
    # element instead has its own step counts and integrator.
    v = rft.Lattice()
    for spec in ELEMENTS:
        e = _build_element(spec)
        # 0 keeps RF-Track's default for the element
        if spec.nsteps > 0:
            e.set_nsteps(spec.nsteps)
        # how finely get_transport_table() (the Beam Variables/Lattice
        # Overlay plots) samples within this element, the Lattice-only
        # equivalent of Volume's tt_dt_mm
        e.set_tt_nsteps(spec.tt_nsteps)
        e.set_sc_nsteps(spec.sc_nsteps)
        # only an element whose field is integrated, not a transfer matrix
        if hasattr(e, "set_odeint_algorithm"):
            e.set_odeint_algorithm(spec.odeint_algorithm)
            e.set_odeint_epsabs(spec.odeint_epsabs)
            e.set_odeint_epsrel(spec.odeint_epsrel)
        # misalignment about the element's entrance, as Volume.add() below:
        # roll about z, pitch about x, yaw about y
        # POSIT: Lattice.append(e, x0, y0, z0, roll, pitch, yaw), in m and rad
        v.append(e, spec.dx, spec.dy, spec.dz, spec.rz, spec.rx, spec.ry)
    return v


def build_bunch():
    twiss = rft.Bunch6d_twiss()
    twiss.beta_x = BUNCH.beta_x
    twiss.beta_y = BUNCH.beta_y
    twiss.alpha_x = BUNCH.alpha_x
    twiss.alpha_y = BUNCH.alpha_y
    twiss.emitt_x = BUNCH.emit_x
    twiss.emitt_y = BUNCH.emit_y
    twiss.sigma_t = BUNCH.sigma_t
    twiss.sigma_pt = BUNCH.sigma_pt
    twiss.disp_x = BUNCH.disp_x
    twiss.disp_px = BUNCH.disp_px
    twiss.disp_y = BUNCH.disp_y
    twiss.disp_py = BUNCH.disp_py
    return rft.Bunch6d_QR(
        BUNCH.mass_mev, BUNCH.charge_nc * rft.nC, BUNCH.charge, BUNCH.pc_mev, twiss, BUNCH.np
    )


def main():
    rft.rng_set_seed(BUNCH.random_seed)
    rft.cvar.number_of_threads = SETTINGS.num_threads

    bunch = build_bunch()
    lume_rftrack.utils.save_particles("initial_particles.npy", bunch)

    volume = build_beamline()
    autophase(volume, bunch)
    # nonzero: RF_Track prints tracking progress to stdout (run.log) as
    # track() advances; after autophase(), which tracks too, so run.log
    # has only the bunch's progress
    # POSIT: _rough_percent_complete() parses a Volume's "t = ... mm/c"
    # and a Lattice's "[###...]  86.1%"
    volume.verbosity = 1

    simulator = lume_rftrack.simulator.RFTrackSimulator(volume, bunch)
    simulator.track()
    lume_rftrack.utils.save_particles(
        "final_particles.npy", simulator.tracked_bunch
    )
    lume_rftrack.utils.save_stats(simulator.beamline, "stats.npy")
    lume_rftrack.utils.save_screens(simulator.beamline, bunch, "screen-{}.npy")
    lume_rftrack.utils.save_bpms(simulator.beamline, "bpms.npy")


def _build_element(spec):
    if spec.kind == "drift":
        e = rft.Drift(spec.l)
    elif spec.kind == "quadrupole_k1":
        # K1 [1/m^2] against the bunch's P/Q, as Elegant defines it; the
        # constructor's own strength argument is K1 * L * P/Q [MeV/m]
        e = rft.Quadrupole(spec.l, math.nan, 0.0)
        e.set_K1(spec.k1, BUNCH.pc_mev / BUNCH.charge)
    elif spec.kind == "quadrupole_gradient":
        e = rft.Quadrupole(spec.l, math.nan, 0.0)
        e.set_gradient(spec.gradient)
    elif spec.kind == "sextupole_k2":
        # k2 [1/m^3] against the bunch's P/Q, as MAD-X defines it
        e = rft.Sextupole(spec.l)
        e.set_K2(BUNCH.pc_mev / BUNCH.charge, spec.k2)
    elif spec.kind == "sextupole_gradient":
        e = rft.Sextupole(spec.l)
        e.set_gradient(spec.gradient)
    elif spec.kind == "rbend":
        e = rft.RBend(spec.l, spec.angle, BUNCH.pc_mev / BUNCH.charge)
    elif spec.kind == "sbend":
        e = rft.SBend(
            spec.l, spec.angle, BUNCH.pc_mev / BUNCH.charge, spec.e1, spec.e2, spec.k1
        )
        e.set_hgap(spec.hgap)
        e.set_fint(spec.fint)
    elif spec.kind == "solenoid_analytic":
        e = rft.Solenoid(spec.l, spec.b_field, spec.radius)
    elif spec.kind == "solenoid_fieldmap":
        field, step, _ = lume_rftrack.utils.load_field_map(spec)
        # the _CINT classes interpolate the map cubically, the others linearly
        e = (
            rft.Static_Magnetic_FieldMap_1d_CINT
            if spec.cubic
            else rft.Static_Magnetic_FieldMap_1d
        )(field, step)
    elif spec.kind == "coil":
        e = rft.Coil(spec.l, spec.b_field, spec.radius)
    elif spec.kind == "corrector":
        e = rft.Corrector(spec.l, spec.h_kick, spec.v_kick)
    elif spec.kind == "cavity_analytic":
        # A standing-wave pi-mode structure of half-wavelength cells,
        # Ez = gradient * sin(n_cells * pi * z / l) on axis, as a field map
        # so RF-Track derives the off-axis fields from it. Pillbox_Cavity
        # can't model it: its field repeats unchanged in every cell, and
        # its off-axis fields for any mode but the first are inconsistent
        # with Maxwell's equations (B in phase with E). 80 points per cell
        # gives the energy gain to 0.03%. Cubic interpolation: the off-axis
        # fields come from Ez's derivatives, which linear interpolation
        # gets wrong (defocusing in place of the ponderomotive focusing).
        # Ez is zero at the irises and ends, peaking mid-cell: peaks at the
        # ends would kick the beam outward on entry with no matching edge.
        # Shorter than half a cell, a single gap of its own length,
        # Ez = gradient * sin^2(pi * z / l): its zero slope at the ends keeps
        # the off-axis fields' energy gain from growing with r^2 / l^2.
        n_cells = round(2.0 * spec.l * spec.frequency_hz / rft.clight)
        if n_cells:
            l = n_cells * rft.clight / (2.0 * spec.frequency_hz)
            z = numpy.linspace(0.0, l, 80 * n_cells + 1)
            ez = numpy.sin(n_cells * numpy.pi * z / l)
        else:
            l = spec.l
            z = numpy.linspace(0.0, l, 81)
            ez = numpy.sin(numpy.pi * z / l) ** 2
        e = rft.RF_FieldMap_1d_CINT(
            (spec.gradient_v_per_m * ez).astype(complex),
            z[1] - z[0],
            l,
            spec.frequency_hz,
            +1,
        )
        e.set_phid(spec.phase_deg)
    elif spec.kind == "cavity_fieldmap":
        field, step, length = lume_rftrack.utils.load_field_map(spec)
        e = (rft.RF_FieldMap_1d_CINT if spec.cubic else rft.RF_FieldMap_1d)(
            field, step, length, spec.frequency_hz, +1
        )
        e.set_phid(spec.phase_deg)
    elif spec.kind == "cavity_fieldmap_2d":
        Er, Ez, hr, hz = lume_rftrack.utils.load_field_map_2d(spec)
        e = (rft.RF_FieldMap_2d_CINT if spec.cubic else rft.RF_FieldMap_2d)(
            Er, Ez, 0, 0, hr, hz, -1, spec.frequency_hz, +1
        )
        e.set_phid(spec.phase_deg)
    elif spec.kind == "screen":
        e = rft.Screen()
        # 0 is unlimited, RF-Track's default
        if spec.width > 0:
            e.set_width(spec.width)
        if spec.height > 0:
            e.set_height(spec.height)
    elif spec.kind == "bpm":
        e = rft.Bpm(spec.l)
        e.set_resolution(spec.resolution)
    else:
        raise AssertionError(f"unsupported element kind={spec.kind}")
    e.set_name(spec.name)
    if spec.aperture_shape != "none":
        e.set_aperture(spec.aperture_x, spec.aperture_y, spec.aperture_shape)
    return e


main()
