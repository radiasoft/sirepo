#!/usr/bin/env python

from pykern.pkcollections import PKDict
import RF_Track as rft
import numpy
import rslume.rftrack
import rslume.rftrack_utils

ELEMENTS = [
    PKDict(
        name='D1',
        elemedge=0.0,
        set_aperture=False,
        aperture_x=0.015,
        aperture_y=0.015,
        aperture_type='circular',
        dx=0,
        dy=0,
        dz=0,
        rx=0,
        ry=0,
        rz=0,
        kind='drift',
        l=1.0,
    ),
    PKDict(
        name='S1',
        elemedge=1.0,
        set_aperture=False,
        aperture_x=0.015,
        aperture_y=0.015,
        aperture_type='circular',
        dx=0,
        dy=0,
        dz=0,
        rx=0,
        ry=0,
        rz=0,
        kind='screen',
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
    charge_nc=1.0,
    emit_x=1.0,
    emit_y=1.0,
    np=100,
    sigma_pt=1.0,
    sigma_t=1.0,
)
SETTINGS = PKDict(
    num_threads=1,
    space_charge=PKDict(
    ),
    tracking_range_m=(
        0.0,
        1.0,
    ),
    volume_dt_mm=0.5,
    volume_tt_dt_mm=10.0,
)


def build_beamline():
    # Volume (rather than Lattice) supports elements at explicit, possibly
    # overlapping absolute z positions -- e.g. a gun cavity's E field and
    # a bucking/focusing solenoid's B field genuinely occupy the same
    # physical space in a real photoinjector.
    v = rft.Volume()
    for spec in ELEMENTS:
        v.add(
            _build_element(spec),
            spec.dx,
            spec.dy,
            spec.elemedge + spec.dz,
            spec.rz,
            spec.rx,
            spec.ry,
        )
    v.set_s0(SETTINGS.tracking_range_m[0])
    v.set_s1(SETTINGS.tracking_range_m[1])
    v.odeint_algorithm = "rkf45"
    v.dt_mm = SETTINGS.volume_dt_mm
    v.tt_dt_mm = SETTINGS.volume_tt_dt_mm
    # nonzero: RF_Track prints tracking progress (e.g. "t = ... mm/c")
    # straight to stdout as track() advances, which is run.log's own
    # content with no further plumbing needed
    v.verbosity = 1
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
    return rft.Bunch6d_QR(
        BUNCH.mass_mev, BUNCH.charge_nc * rft.nC, BUNCH.charge, BUNCH.pc_mev, twiss, BUNCH.np
    )


def main():
    rft.rng_set_seed(BUNCH.random_seed)
    rft.cvar.number_of_threads = SETTINGS.num_threads

    bunch = build_bunch()
    rslume.rftrack_utils.save_particles("initial_particles.npy", bunch)

    volume = build_beamline()

    model = rslume.rftrack.build_model(ELEMENTS, volume, bunch)
    model.reset()
    rslume.rftrack_utils.save_particles(
        "final_particles.npy", model.simulator.tracked_bunch
    )
    rslume.rftrack_utils.save_stats(model.simulator.beamline)
    rslume.rftrack_utils.save_screens(model.simulator.beamline, bunch)
    rslume.rftrack_utils.save_bpms(model.simulator.beamline)


def _build_element(spec):
    if spec.kind == "drift":
        e = rft.Drift(spec.l)
    elif spec.kind == "quadrupole_k1":
        e = rft.Quadrupole(spec.l, spec.k1)
    elif spec.kind == "quadrupole_gradient":
        e = rft.Quadrupole(spec.l, float("nan"), 0.0)
        e.set_gradient(spec.gradient)
    elif spec.kind == "rbend":
        e = rft.RBend(spec.l, spec.angle, BUNCH.pc_mev / BUNCH.charge)
    elif spec.kind == "solenoid_analytic":
        e = rft.Solenoid(spec.l, spec.b_field, spec.radius)
    elif spec.kind == "solenoid_fieldmap":
        field, step, _ = rslume.rftrack_utils.load_field_map(spec)
        e = rft.Static_Magnetic_FieldMap_1d(field, step)
    elif spec.kind == "corrector":
        e = rft.Corrector(spec.l, spec.h_kick, spec.v_kick)
    elif spec.kind == "cavity_analytic":
        l_cell = rft.clight / (2.0 * spec.frequency_hz)
        n_cells = max(1, round(spec.l / l_cell))
        a = numpy.zeros(1)
        a[-1] = spec.gradient_v_per_m
        e = rft.Pillbox_Cavity(a, spec.frequency_hz, l_cell, n_cells)
        e.set_phid(spec.phase_deg)
    elif spec.kind == "cavity_fieldmap":
        field, step, length = rslume.rftrack_utils.load_field_map(spec)
        e = rft.RF_FieldMap_1d(field, step, length, spec.frequency_hz, +1)
        e.set_phid(spec.phase_deg)
    elif spec.kind == "cavity_fieldmap_2d":
        Er, Ez, hr, hz = rslume.rftrack_utils.load_field_map_2d(spec)
        e = rft.RF_FieldMap_2d(Er, Ez, 0, 0, hr, hz, -1, spec.frequency_hz, +1)
        e.set_phid(spec.phase_deg)
    elif spec.kind == "screen":
        e = rft.Screen()
    elif spec.kind == "bpm":
        e = rft.Bpm(spec.l)
    else:
        raise AssertionError(f"unsupported element kind={spec.kind}")
    # Explicitly pin t0 to 0.0 on every cavity/screen: confirmed
    # empirically that Volume.track() internally re-autophases every RF
    # element (and every Screen) from scratch if ANY of them has
    # t0_is_set() False, regardless of phid, silently overriding an
    # explicitly-set phase with Autophase off.
    #
    # Only emitted when the autophase() function below WON'T run:
    # confirmed empirically that Volume.unset_t0() -- the first thing
    # that function does -- does NOT clear an element's t0 once set()
    # was ever called on it directly, even to 0.0. Pinning t0 here
    # unconditionally would silently defeat the real autophase() search
    # that follows, leaving every cavity stuck at 0.0 instead of a
    # freshly-derived value (confirmed: the whole beamline ends up
    # unphased, same failure mode as never phasing at all, just
    # disguised since t0_is_set() now reads True).
    if spec.kind in ("cavity_analytic", "cavity_fieldmap", "cavity_fieldmap_2d", "screen"):
        e.set_t0(0.0)
    e.set_name(spec.name)
    if spec.set_aperture:
        e.set_aperture(spec.aperture_x, spec.aperture_y, spec.aperture_type)
    return e


# Not "if __name__ == '__main__'": Sirepo runs this file via
# pykern.pkrunpy.run_path_as_module(), which execs it with __name__ set to
# a name derived from the filename, never "__main__" -- that guard would
# silently skip main() entirely under Sirepo's own execution path (no
# error, just none of the actual work happening) while still appearing to
# work when run standalone via `python3 parameters.py`, which is how this
# bug was first missed.
main()
