"""Write the lume_rftrack archives tests/template/import_file_test.py imports

Run from the repository root after lume_rftrack's archive format changes:

    python tests/template/rftrack_data/import_archives.py

then regenerate each case's pythonSource.txt.

rftrack-fieldmap is a Lattice with one element of every class the import
supports, elliptical and rectangular apertures, a solenoid whose aperture
isn't its radius, a sextupole with its own step counts and integrator,
scaling factors on the coil, sextupole and corrector, a sized screen, a BPM
resolution, a quadrupole repeated identically (one element) and with a
different gradient (renamed), an unnamed drift, a misaligned sextupole, and
RF and static field maps with power and scaling factors. rftrack-volume is
a Volume with overlapping field maps, a transversely offset corrector, its
integrator settings (with error tolerances and a maximum tracking time) and
tracking range, and space charge.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import numpy
import RF_Track as rft
from lume_rftrack.simulator import RFTrackSimulator
from pykern import pkio

_DIR = pkio.py_path(__file__).dirpath().dirpath().join("import_file_data")

_PC = 100.0

_Z = numpy.linspace(0.0, 0.1, 41)


def main():
    _lattice().archive(str(_DIR.join("rftrack-fieldmap.in", "archive.h5")))
    s = _volume()
    s.archive(
        str(_DIR.join("rftrack-volume.in", "archive.h5")),
        space_charge=dict(
            kind="pic", dt_mm=3.0, grid=(8, 8, 16), mirror_m=0.0, smooth=0.5
        ),
    )


def _bunch():
    t = rft.Bunch6d_twiss()
    t.beta_x = t.beta_y = 5.0
    t.emitt_x = t.emitt_y = 1.0
    t.sigma_t = 0.1
    t.sigma_pt = 0.1
    return rft.Bunch6d_QR(rft.electronmass, rft.nC, -1.0, _PC, t, 100)


def _lattice():
    def _quad(gradient):
        q = rft.Quadrupole(0.1)
        q.set_gradient(gradient)
        q.set_aperture(0.01, 0.02, "circular")
        return q

    c = rft.RF_FieldMap_1d(_rf_map(), _Z[1] - _Z[0], 0.1, 1.3e9, 1)
    c.set_phid(10.0)
    c.set_P_map(1.0)
    c.set_P_actual(4.0)
    sol = rft.Static_Magnetic_FieldMap_1d(
        0.2 * numpy.exp(-(((_Z - 0.05) / 0.02) ** 2)), _Z[1] - _Z[0]
    )
    sol.set_scaling_factor(1.5)
    sext = rft.Sextupole(0.1)
    sext.set_gradient(40.0)
    sext.set_nsteps(7)
    sext.set_tt_nsteps(5)
    sext.set_sc_nsteps(2)
    sext.set_odeint_algorithm("rk4")
    sext.set_odeint_epsabs(1e-6)
    sext.set_odeint_epsrel(1e-5)
    sext.set_scaling_factor(1.2)
    bend = rft.SBend(0.3, 0.05, _PC / -1.0, 0.01, 0.02)
    bend.set_hgap(0.02)
    bend.set_fint(0.5)
    cor = rft.Corrector(0.02)
    cor.set_strength(1e-3, 2e-3)
    cor.set_scaling_factor(2.0)
    coil = rft.Coil(0.2, 0.1, 0.05)
    coil.set_scaling_factor(1.5)
    bpm = _rectangular(rft.Bpm(0.05))
    bpm.set_resolution(0.1)
    screen = rft.Screen()
    screen.set_width(0.05)
    screen.set_height(0.04)
    elements = (
        ("D0", rft.Drift(0.05)),
        ("Q1", _quad(2.5)),
        ("Q1", _quad(2.5)),
        ("Q1", _quad(-2.5)),
        ("", rft.Drift(0.1)),
        ("SX1", sext),
        ("B1", bend),
        ("COR1", cor),
        ("C1", c),
        ("C2", rft.RF_FieldMap_1d_CINT(_rf_map(), _Z[1] - _Z[0], 0.1, 1.3e9, 1)),
        ("C3", _rf_map_2d()),
        ("SOL1", sol),
        ("SOL2", _circular(rft.Solenoid(0.2, 0.1, 0.03), 0.02)),
        ("COIL1", coil),
        ("BPM1", bpm),
        ("S1", screen),
    )
    res = rft.Lattice()
    for n, e in elements:
        e.set_name(n)
        res.append(e)
    o = numpy.zeros((len(elements), 7))
    o[:, 3] = 1.0
    # mm, then rotations about x, y, z
    o[5] = [0.5, -0.3, 0.0, 1.0, 1e-3, 2e-3, 3e-3]
    res.set_elements_offsets(o)
    res.autophase(
        rft.Bunch6d(rft.electronmass, 0.0, -1.0, numpy.array([0, 0, 0, 0, 0, _PC]))
    )
    return RFTrackSimulator(res, _bunch())


def _circular(element, radius):
    element.set_aperture(radius, radius, "circular")
    return element


def _rectangular(element):
    element.set_aperture(0.02, 0.01, "rectangular")
    return element


def _rf_map():
    return (20e6 * numpy.sin(numpy.pi * _Z / 0.1)).astype(complex)


def _rf_map_2d():
    nz, nr, hz, hr = 21, 5, 0.005, 0.002
    z = numpy.arange(nz) * hz
    r = numpy.arange(nr) * hr
    res = rft.RF_FieldMap_2d(
        numpy.outer(1e6 * numpy.cos(numpy.pi * z / z[-1]), r / r[-1]),
        numpy.outer(20e6 * numpy.sin(numpy.pi * z / z[-1]), numpy.ones(nr)),
        0,
        0,
        hr,
        hz,
        -1,
        3e9,
        1,
    )
    res.set_P_actual(2.0)
    return res


def _volume():
    v = rft.Volume()
    c = rft.RF_FieldMap_1d(_rf_map(), _Z[1] - _Z[0], 0.1, 1.3e9, 1)
    c.set_name("C1")
    c.set_t0(0.0)
    v.add(c, 0.0, 0.0, 0.0)
    sol = rft.Static_Magnetic_FieldMap_1d(
        0.2 * numpy.exp(-(((_Z - 0.05) / 0.02) ** 2)), _Z[1] - _Z[0]
    )
    sol.set_name("SOL1")
    # overlaps the cavity
    v.add(sol, 0.0, 0.0, 0.05)
    cor = rft.Corrector(0.02)
    cor.set_name("COR1")
    cor.set_strength(1e-3, 0.0)
    v.add(cor, 1e-3, -2e-3, 0.3)
    s = rft.Screen()
    s.set_name("S1")
    s.set_t0(0.0)
    v.add(s, 0.0, 0.0, 0.5)
    v.set_s0(0.0)
    v.set_s1(0.6)
    v.dt_mm = 0.2
    v.tt_dt_mm = 5.0
    v.odeint_algorithm = "rk2"
    v.odeint_epsabs = 1e-5
    v.odeint_epsrel = 1e-4
    v.t_max_mm = 2000.0
    return RFTrackSimulator(v, rft.Bunch6dT(_bunch()))


if __name__ == "__main__":
    main()
