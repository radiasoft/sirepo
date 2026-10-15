#!/usr/bin/env python
"""
Simulation notes:
    RF-Track tutorial 15, Photoinjector simulation: https://gitlab.cern.ch/rf-track/rf-track-jupyter-notebooks

"""

from pykern.pkcollections import PKDict
import RF_Track as rft
import numpy
import rslume.rftrack
import rslume.rftrack_utils

ELEMENTS = [
    PKDict(
        name='Gun',
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
        kind='cavity_fieldmap',
        cubic=True,
        file='CAVITY-fieldMapFile.GUN_ideal_SF_100.txt',
        rescale_mode='peak',
        target_field=100000000.0,
        frequency_hz=2998550000.0,
        phase_deg=140.0,
    ),
    PKDict(
        name='Sol',
        elemedge=-1.063,
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
        kind='solenoid_fieldmap',
        cubic=True,
        file='SOLENOID-fieldMapFile.profile_califes_bon_B1_285_B3_338.txt',
        rescale_mode='peak',
        target_field=0.25,
    ),
]
BUNCH = PKDict(
    charge=-1.0,
    mass_mev=0.51099895069,
    pc_mev=100.0,
    random_seed=5489,
    c_sig_t=3,
    c_sig_x=3,
    c_sig_y=3,
    cathode=True,
    dist_pz='fd_300',
    dist_x='g',
    dist_y='g',
    dist_z='gaussian',
    e_photon=4.73,
    lt=0.006,
    noise_reduc=True,
    np=5000,
    phi_eff=3.5,
    q_total_nc=0.1,
    ref_clock=0,
    ref_ekin=0,
    ref_zpos=0,
    rt=0.0003,
    sig_t=0.0012,
    sig_x=0.8,
    sig_y=0.8,
    species='electrons',
)
SETTINGS = PKDict(
    num_threads=1,
    space_charge=PKDict(
        kind='pic',
        dt_mm=1.0,
        grid=(
            32,
            32,
            32,
        ),
        mirror_m=0.0,
        smooth=0.5,
    ),
    tracking_range_m=(
        0.0,
        1.0,
    ),
    odeint_algorithm='rk2',
    volume_dt_mm=0.1,
    volume_tt_dt_mm=5.0,
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
    v.odeint_algorithm = SETTINGS.odeint_algorithm
    v.dt_mm = SETTINGS.volume_dt_mm
    v.tt_dt_mm = SETTINGS.volume_tt_dt_mm
    # nonzero: RF_Track prints tracking progress (e.g. "t = ... mm/c")
    # straight to stdout as track() advances, which is run.log's own
    # content with no further plumbing needed
    v.verbosity = 1
    return v


def build_bunch():
    # Cathode emission: particles start essentially at rest and are
    # generated directly from the photocathode's laser/emission model,
    # rather than from an already-moving analytic (Twiss) distribution.
    g = rft.Bunch6dT_Generator()
    g.species = BUNCH.species
    g.cathode = BUNCH.cathode
    g.noise_reduc = BUNCH.noise_reduc
    g.q_total = BUNCH.q_total_nc
    g.ref_ekin = BUNCH.ref_ekin
    g.ref_zpos = BUNCH.ref_zpos
    g.ref_clock = BUNCH.ref_clock
    g.phi_eff = BUNCH.phi_eff
    g.e_photon = BUNCH.e_photon
    g.dist_x = BUNCH.dist_x
    g.dist_y = BUNCH.dist_y
    g.sig_x = BUNCH.sig_x
    g.sig_y = BUNCH.sig_y
    g.dist_z = BUNCH.dist_z
    g.rt = BUNCH.rt
    g.lt = BUNCH.lt
    g.sig_t = BUNCH.sig_t
    g.c_sig_x = BUNCH.c_sig_x
    g.c_sig_y = BUNCH.c_sig_y
    g.c_sig_t = BUNCH.c_sig_t
    g.dist_pz = BUNCH.dist_pz
    return rft.Bunch6dT(g, BUNCH.np)


def main():
    rft.rng_set_seed(BUNCH.random_seed)
    rft.cvar.number_of_threads = SETTINGS.num_threads

    bunch = build_bunch()
    rslume.rftrack_utils.save_particles("initial_particles.npy", bunch)

    volume = build_beamline()
    rslume.rftrack_utils.apply_space_charge(volume, SETTINGS.space_charge)

    model = rslume.rftrack.build_model(ELEMENTS, volume, bunch)
    model.reset()
    rslume.rftrack_utils.save_particles(
        "final_particles.npy", model.simulator.tracked_bunch
    )
    rslume.rftrack_utils.save_stats(model.simulator.beamline, "stats.npy")
    rslume.rftrack_utils.save_screens(
        model.simulator.beamline, bunch, "screen-{}.npy"
    )
    rslume.rftrack_utils.save_bpms(model.simulator.beamline, "bpms.npy")


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
        # the _CINT classes interpolate the map cubically, the others linearly
        e = (
            rft.Static_Magnetic_FieldMap_1d_CINT
            if spec.cubic
            else rft.Static_Magnetic_FieldMap_1d
        )(field, step)
    elif spec.kind == "corrector":
        e = rft.Corrector(spec.l, spec.h_kick, spec.v_kick)
    elif spec.kind == "cavity_analytic":
        # A standing-wave pi-mode structure of half-wavelength cells,
        # Ez = gradient * cos(n_cells * pi * z / l) on axis, as a field map
        # so RF-Track derives the off-axis fields from it. Pillbox_Cavity
        # can't model it: its field repeats unchanged in every cell, and
        # its off-axis fields for any mode but the first are inconsistent
        # with Maxwell's equations (B in phase with E). 40 points per cell
        # gives the energy gain to 0.05%.
        n_cells = max(1, round(2.0 * spec.l * spec.frequency_hz / rft.clight))
        l = n_cells * rft.clight / (2.0 * spec.frequency_hz)
        z = numpy.linspace(0.0, l, 40 * n_cells + 1)
        e = rft.RF_FieldMap_1d(
            (spec.gradient_v_per_m * numpy.cos(n_cells * numpy.pi * z / l)).astype(complex),
            z[1] - z[0],
            l,
            spec.frequency_hz,
            +1,
        )
        e.set_phid(spec.phase_deg)
    elif spec.kind == "cavity_fieldmap":
        field, step, length = rslume.rftrack_utils.load_field_map(spec)
        e = (rft.RF_FieldMap_1d_CINT if spec.cubic else rft.RF_FieldMap_1d)(
            field, step, length, spec.frequency_hz, +1
        )
        e.set_phid(spec.phase_deg)
    elif spec.kind == "cavity_fieldmap_2d":
        Er, Ez, hr, hz = rslume.rftrack_utils.load_field_map_2d(spec)
        e = (rft.RF_FieldMap_2d_CINT if spec.cubic else rft.RF_FieldMap_2d)(
            Er, Ez, 0, 0, hr, hz, -1, spec.frequency_hz, +1
        )
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
