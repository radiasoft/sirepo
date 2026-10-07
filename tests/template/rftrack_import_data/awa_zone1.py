#!/usr/bin/env python
"""
Simulation notes:
    Reproduces zone_1.ipynb's own default awa_params exactly: solenoid currents/fields and PIC space charge (grid 8x8x16, smooth=0.5, mirror=0.0) match the notebook's Part 1.4 setup, rather than the hand-tuned focusing values used in the "AWA Zone 1" example.

Autophase uses a single at-rest reference particle (more numerically stable, per findings from building this feature) rather than the notebook's own zone1.autophase(Ref0), which targets the full macroparticle bunch. Both give matching final beam energy (~62.5 MeV) and transmission, confirming the acceleration physics agrees. However, the two methods converge to different (but equally valid, 360-degree-periodic) on-crest phase solutions per cavity, so a frozen on-axis Ez(s) snapshot (Ez/Bz stat columns, or the notebook's plot_diagnostics_overview panel (a)) will look different between them for every cavity after the Gun: this sim shows a uniform ~22 MV/m peak at each of L1-L6, while the notebook's own rendered plot (using its literal, less stable Ref0-based autophase) shows scattered, reduced peaks (seen directly: Gun ~57, L1 ~12, L2 ~22, L3 ~4, L4 ~21, L5 ~3, L6 ~17 MV/m). This is expected: a fixed-time field snapshot is sensitive to which 360-degree branch autophase happens to land on for each downstream cavity, since on-crest acceleration (cos(phase)=1) is unique only modulo 360 degrees. It is not a bug in either implementation -- the beam sees correct on-crest acceleration either way.

A second, independent source of the same branch ambiguity: the notebook's own cells 16-17 convert autophase's t0 into a phid value (phid = -t0/period*360) and then REBUILD the entire lattice from scratch (zone1Builder(params=awa_params)) with that phid baked in at t0=0, rather than reusing the already-autophased volume as-is. This conversion is lossy with respect to which 360-degree-periodic branch gets selected -- verified by testing three variants against the same autophased state: (1) reuse the volume directly, no conversion (this sim's approach): Gun 80, L1-L6 uniform ~22 MV/m; (2) the notebook's own full rebuild via zone1Builder: Gun ~57, L1 ~12, L2 ~22, L3 ~4, L4 ~21, L5 ~3, L6 ~17 MV/m; (3) an in-place rf.set_t0(0)/set_phid() update with no rebuild (matching this codebase's own preproc.safe_autophase_setPhid helper): yet another distinct scattered pattern (Gun ~63, L1 ~20, L2 ~22, L3 ~17, L4 ~22, L5 ~16, L6 ~11 MV/m). All three give the same final beam energy (~62.5 MeV) -- only the frozen Ez(s) snapshot differs. So it is not specifically 'rebuild vs. in-place' that matters: any hand conversion of t0 into phid via that formula can land on a different phase branch than autophase() was actually using internally, regardless of how the resulting phid is applied. Only reusing t0/the autophased volume completely as-is, with no phid conversion step at all, reliably preserves the original branch.

"""

from pykern.pkcollections import PKDict
import RF_Track as rft
import numpy

ELEMENTS = [
    PKDict(
        name='Gun',
        elemedge=0,
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
        file='CAVITY-fieldMapFile.rf_gunG4.dat',
        rescale_mode='peak',
        target_field=80000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='SolBF',
        elemedge=-0.5,
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
        file='SOLENOID-fieldMapFile.sol_bucking-focusing_pm550A.dat',
        rescale_mode='factor',
        scale_factor=0.0001,
    ),
    PKDict(
        name='SolM',
        elemedge=0,
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
        file='SOLENOID-fieldMapFile.sol_matching_m440A.dat',
        rescale_mode='factor',
        scale_factor=0.0001,
    ),
    PKDict(
        name='L1',
        elemedge=0.576433,
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
        file='CAVITY-fieldMapFile.linac.dat',
        rescale_mode='peak',
        target_field=22000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='SolL1',
        elemedge=1.544,
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
        file='SOLENOID-fieldMapFile.sol_linacLB_500A.dat',
        rescale_mode='factor',
        scale_factor=2.0000000000000002e-07,
    ),
    PKDict(
        name='YAG1',
        elemedge=2.9,
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
    PKDict(
        name='L2',
        elemedge=3.306433,
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
        file='CAVITY-fieldMapFile.linac.dat',
        rescale_mode='peak',
        target_field=22000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='SolL2',
        elemedge=4.12,
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
        file='SOLENOID-fieldMapFile.sol_linac_500A.dat',
        rescale_mode='factor',
        scale_factor=2.0000000000000002e-07,
    ),
    PKDict(
        name='L3',
        elemedge=4.856433,
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
        file='CAVITY-fieldMapFile.linac.dat',
        rescale_mode='peak',
        target_field=22000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='YAG2',
        elemedge=6.292,
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
    PKDict(
        name='SolL4',
        elemedge=5.881,
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
        file='SOLENOID-fieldMapFile.sol_linac_500A.dat',
        rescale_mode='factor',
        scale_factor=2.0000000000000002e-07,
    ),
    PKDict(
        name='L4',
        elemedge=6.986433,
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
        file='CAVITY-fieldMapFile.linac.dat',
        rescale_mode='peak',
        target_field=22000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='L5',
        elemedge=8.326433,
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
        file='CAVITY-fieldMapFile.linac.dat',
        rescale_mode='peak',
        target_field=22000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='YAG3',
        elemedge=9.525,
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
    PKDict(
        name='L6',
        elemedge=9.736433,
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
        file='CAVITY-fieldMapFile.linac.dat',
        rescale_mode='peak',
        target_field=22000000.0,
        frequency_hz=1300000000,
        phase_deg=0.0,
    ),
    PKDict(
        name='YAG4',
        elemedge=11.372,
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
PHASE_SPACE_FIELDS = "%X %xp %Y %yp %Z %t0 %Px %Py %Pz %P %E %K"
# Volume.get_bunch_at_screens() always returns Bunch6d-typed bunches, even
# when the tracked bunch is a Bunch6dT (cathode distribution), so the token
# string for screen-captured bunches can differ from the one above.
PHASE_SPACE_FIELDS_SCREEN = "%X %xp %Y %yp %Z %dt %Px %Py %Pz %P %E %K"
# RF_Track's native phase-space units are mm, mrad, and MeV/c; rescale to
# base SI units (m, rad, eV/c, eV, s) to match impact-t's convention.
PHASE_SPACE_SCALE = numpy.array([0.001, 0.001, 0.001, 0.001, 0.001, 3.3356409519815207e-12, 1000000.0, 1000000.0, 1000000.0, 1000000.0, 1000000.0, 1000000.0])

BUNCH = PKDict(
    charge=-1.0,
    mass_mev=0.51099895069,
    pc_mev=1,
    random_seed=5489,
    c_sig_t=3,
    c_sig_x=3,
    c_sig_y=3,
    cathode=True,
    dist_pz='fd_300',
    dist_x='r',
    dist_y='g',
    dist_z='plateau',
    e_photon=4.73,
    lt=0.006,
    noise_reduc=True,
    np=10000,
    phi_eff=3.5,
    q_total_nc=1,
    ref_clock=0,
    ref_ekin=0,
    ref_zpos=0,
    rt=0.0003,
    sig_x=1.67,
    species='electrons',
)
SETTINGS = PKDict(
    num_threads=1,
    space_charge=PKDict(
        dt_mm=3,
        grid=(
            8,
            8,
            16,
        ),
        mirror_m=0,
        smooth=0.5,
    ),
    tracking_range_m=(
        0,
        11.372,
    ),
    volume_dt_mm=0.5,
    volume_tt_dt_mm=10.0,
)

STAT_FIELDS = "%mean_Z %beta_x %beta_y %alpha_x %alpha_y %emitt_x %emitt_y %emitt_4d %beta_z %alpha_z %emitt_z %sigma_X %sigma_Y %sigma_Z %sigma_Pz %sigma_E %disp_x %disp_y %disp_px %disp_py %mean_X %mean_Y %mean_Px %mean_Py %mean_K %mean_E %mean_P %rmax %rmax90 %rmax99 %rmax99.9 %N"
STAT_SCALE = numpy.array([0.001, 1, 1, 1, 1, 1e-06, 1e-06, 1e-06, 1, 1, 1e-06, 0.001, 0.001, 0.001, 1000000.0, 1000000.0, 1, 1, 1, 1, 0.001, 0.001, 1000000.0, 1000000.0, 1000000.0, 1000000.0, 1000000.0, 0.001, 0.001, 0.001, 0.001, 1, 1, 1])


def apply_space_charge(volume):
    sc_settings = SETTINGS.space_charge
    volume.sc_dt_mm = sc_settings.dt_mm
    sc = rft.SpaceCharge_PIC_FreeSpace(*sc_settings.grid)
    sc.set_smooth(sc_settings.smooth)
    sc.set_mirror(sc_settings.mirror_m)
    # rft.cvar.SC_engine (a process-global) rather than
    # Volume.set_sc_engine(): the latter does not apply space-charge
    # forces the same way for a multi-element Volume.
    rft.cvar.SC_engine = sc


def autophase(volume):
    # Autophase against a single on-axis reference particle, then track
    # the real bunch through this SAME (now-phased) volume; do not
    # rebuild it. Volume.autophase() sets each RF element's internal t0
    # directly and .track() uses that state as-is -- get_phid() does not
    # reflect it (it always reads back the phid the element was
    # constructed with), so reading it back to "convert" t0 into an
    # equivalent phid for a rebuilt volume silently produces the unphased
    # result instead of the true autophased state.
    # A Cathode or From File reference particle starts at rest
    # (X,Px,Y,Py,Z,Pz all 0), not at the design momentum, since both are
    # snapshots of a bunch that begins from (near) rest, not an
    # already-accelerated analytic (Twiss) distribution.
    p0 = rft.Bunch6dT(
        numpy.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, BUNCH.mass_mev, BUNCH.charge, 1.0, 0.0]])
    )
    volume.unset_t0()
    volume.autophase(p0)


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
    v.verbosity = 0
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
    g.dist_z = BUNCH.dist_z
    g.rt = BUNCH.rt
    g.lt = BUNCH.lt
    g.c_sig_x = BUNCH.c_sig_x
    g.c_sig_y = BUNCH.c_sig_y
    g.c_sig_t = BUNCH.c_sig_t
    g.dist_pz = BUNCH.dist_pz
    return rft.Bunch6dT(g, BUNCH.np)


def main():
    rft.rng_set_seed(BUNCH.random_seed)
    rft.cvar.number_of_threads = SETTINGS.num_threads

    bunch = build_bunch()
    save_particles("initial_particles.npy", bunch, PHASE_SPACE_FIELDS)

    volume = build_beamline()
    autophase(volume)
    apply_space_charge(volume)

    tracked = volume.track(bunch)
    save_particles("final_particles.npy", tracked, PHASE_SPACE_FIELDS)
    save_stats(volume)
    save_screens(volume)


def save_particles(filename, bunch, fields):
    numpy.save(filename, bunch.get_phase_space(fields) * PHASE_SPACE_SCALE)


def save_screens(volume):
    for i, bunch in enumerate(volume.get_bunch_at_screens()):
        save_particles(f"screen-{i}.npy", bunch, PHASE_SPACE_FIELDS_SCREEN)


def save_stats(volume):
    t = numpy.array(volume.get_transport_table(STAT_FIELDS))
    # On-axis Ez/Bz: a direct field query (independent of the tracked
    # beam) at x=y=0 and t=0, sampled at the same s positions as the
    # transport table, so it can be selected as another y-axis column
    # alongside the beam statistics.
    volume.set_t0(0)
    e, b = volume.get_field(0.0, 0.0, t[:, 0], 0.0)
    volume.unset_t0()
    t = numpy.hstack([t, numpy.array(e)[:, 2:3], numpy.array(b)[:, 2:3]])
    numpy.save("stats.npy", t * STAT_SCALE)


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
        field, step, _ = _load_field_map(spec)
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
        field, step, length = _load_field_map(spec)
        e = rft.RF_FieldMap_1d(field, step, length, spec.frequency_hz, +1)
        e.set_phid(spec.phase_deg)
    elif spec.kind == "screen":
        e = rft.Screen()
    else:
        raise AssertionError(f"unsupported element kind={spec.kind}")
    e.set_name(spec.name)
    e.set_aperture(spec.aperture_x, spec.aperture_y, spec.aperture_type)
    return e


def _load_field_map(spec):
    t = numpy.loadtxt(spec.file)
    s = t[:, 0]
    step = (s.max() - s.min()) / (len(s) - 1)
    length = s.max() - s.min()
    field = t[:, 1]
    if spec.rescale_mode == "factor":
        field = field * spec.scale_factor
    else:
        field = field / numpy.max(numpy.abs(field)) * spec.target_field
    return field, step, length


# Not "if __name__ == '__main__'": Sirepo runs this file via
# pykern.pkrunpy.run_path_as_module(), which execs it with __name__ set to
# a name derived from the filename, never "__main__" -- that guard would
# silently skip main() entirely under Sirepo's own execution path (no
# error, just none of the actual work happening) while still appearing to
# work when run standalone via `python3 parameters.py`, which is how this
# bug was first missed.
main()
