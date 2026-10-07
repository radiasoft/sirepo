"""PyTest for :mod:`sirepo.template.rftrack_import_mapper`

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_cathode_bunch():
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

g = rft.Bunch6dT_Generator()
g.species = "electron"
g.q_total = 0.5
g.sig_x = 0.001
g.lt = 2e-12
g.rt = 0.5e-12
g.c_sig_t = 3.0
g.c_sig_x = 2.5
g.c_sig_y = 2.5
g.e_photon = 2.1
g.phi_eff = 1.57
g.noise_reduc = True
p0 = rft.Bunch6dT(g, 10000)
"""
    )
    b = rftrack_import_mapper.map_bunch(res.calls)
    pkeq("electron", b.particle)
    pkeq(0.5, b.charge_nC)
    pkeq(10000, b.np)
    pkeq(0.001, b.sigX)
    pkeq(2e-12, b.flatTopLength)
    pkeq(5e-13, b.riseTime)
    pkeq(3.0, b.cutoffT)
    pkeq(2.5, b.cutoffX)
    pkeq(2.5, b.cutoffY)
    pkeq(2.1, b.ePhoton)
    pkeq(1.57, b.phiEff)
    pkeq("1", b.noiseReduc)


def test_elements():
    """One of each of the 7 element types the schema supports, each built
    and placed exactly as rftrack.py's own generated _build_element does
    (set_name + set_aperture before Volume.add), to verify the mapper's
    output matches what the script actually asked for.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

v = rft.Volume()


def place(e, name, ax, ay, dx, dy, z, rz, rx, ry):
    e.set_name(name)
    e.set_aperture(ax, ay, "circular")
    v.add(e, dx, dy, z, rz, rx, ry)


place(rft.Drift(1.5), "D1", 0.02, 0.02, 0, 0, 0.0, 0, 0, 0)
place(rft.Quadrupole(0.2, 3.0), "Q1", 0.015, 0.015, 0, 0, 1.5, 0, 0, 0)

qg = rft.Quadrupole(0.3, float("nan"), 0.0)
qg.set_gradient(5.0)
place(qg, "Q2", 0.015, 0.015, 0, 0, 1.8, 0, 0, 0)

place(rft.RBend(0.5, 0.1, 938.272), "B1", 0.03, 0.03, 0.001, 0.002, 2.3, 0.01, 0.02, 0.03)
place(rft.Solenoid(0.4, 0.8, 0.05), "S1", 0.05, 0.05, 0, 0, 2.9, 0, 0, 0)
place(rft.Corrector(0.1, 0.001, -0.002), "C1", 0.02, 0.02, 0, 0, 3.3, 0, 0, 0)

freq = 2.856e9
l_cell = rft.clight / (2.0 * freq)
a = numpy.zeros(1)
a[-1] = 20e6
cav = rft.Pillbox_Cavity(a, freq, l_cell, 5)
cav.set_phid(30.0)
place(cav, "gun", 0.04, 0.04, 0, 0, 3.5, 0, 0, 0)

place(rft.Screen(), "SCR1", 0.02, 0.02, 0, 0, 4.0, 0, 0, 0)
"""
    )
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq("absolute", element_position)
    pkeq([], warnings)
    pkeq(["D1", "Q1", "Q2", "B1", "S1", "C1", "gun", "SCR1"], [x.name for x in e])

    d = e[0]
    pkeq("DRIFT", d.type)
    pkeq(1.5, d.l)
    pkeq(0.02, d.aperture_x)
    pkeq(0.02, d.aperture_y)
    pkeq(0.0, d.elemedge)

    q1 = e[1]
    pkeq("QUADRUPOLE", q1.type)
    pkeq("k1", q1.strengthType)
    pkeq(0.2, q1.l)
    pkeq(3.0, q1.k1)
    pkeq(1.5, q1.elemedge)

    q2 = e[2]
    pkeq("gradient", q2.strengthType)
    pkeq(0.3, q2.l)
    pkeq(5.0, q2.gradient)

    b = e[3]
    pkeq("RBEND", b.type)
    pkeq(0.1, b.angle)
    pkeq(0.001, b.dx)
    pkeq(0.002, b.dy)
    pkeq(0.02, b.rx)
    pkeq(0.03, b.ry)
    pkeq(0.01, b.rz)

    s = e[4]
    pkeq("SOLENOID", s.type)
    pkeq("analytic", s.fieldSource)
    pkeq(0.4, s.l)
    pkeq(0.8, s.b_field)

    c = e[5]
    pkeq("CORRECTOR", c.type)
    pkeq(0.1, c.l)
    pkeq(0.001, round(c.h_kick, 6))
    pkeq(-0.002, round(c.v_kick, 6))

    cav = e[6]
    pkeq("CAVITY", cav.type)
    pkeq("analytic", cav.fieldSource)
    pkeq(2.856e9, cav.frequency)
    pkeq(30.0, round(cav.phase, 6))
    pkeq(20.0, round(cav.gradient, 6))

    pkeq("SCREEN", e[7].type)


def test_fieldmap_missing_source_file():
    """The realistic case: the script's own _load_field_map()-style
    numpy.loadtxt() of the field map file this simulation would have had
    in its sim_db lib directory, which this isolated import subprocess's
    scratch directory never has a copy of -- fieldMapFile should still
    come back set to that filename (stripped of rftrack.py's own
    "{type}-fieldMapFile." lib-file prefix), with a warning that it needs
    re-uploading, so the generic lattice import dialog's existing
    "missing files" prompt (the same one every other lattice-code
    importer already gets) picks it up.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

field_data = numpy.loadtxt("SOLENOID-fieldMapFile.coil.dat")
s = field_data[:, 0]
step = (s.max() - s.min()) / (len(s) - 1)
field = field_data[:, 1] / numpy.max(numpy.abs(field_data[:, 1])) * 0.8
v = rft.Volume()
sol = rft.Static_Magnetic_FieldMap_1d(field, step)
sol.set_name("SOLFM")
sol.set_aperture(0.05, 0.05, "circular")
v.add(sol, 0, 0, 0.0, 0, 0, 0)
"""
    )
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq(1, len(e))
    pkeq("SOLENOID", e[0].type)
    pkeq("fieldMap", e[0].fieldSource)
    pkeq("coil.dat", e[0].fieldMapFile)
    # not a length derived from the placeholder array
    # _stub_missing_data_files() substitutes for the missing file (its
    # made-up s range would otherwise silently become a specific-looking
    # but fabricated "length") -- 0 is an honest "not recoverable"
    pkeq(0, e[0].l)
    pkeq(1, len(warnings))
    pkeq(True, "coil.dat" in warnings[0])


def test_fieldmap_no_loadtxt_call():
    """No numpy.loadtxt() preceded this construction at all (e.g. the
    field array was computed inline, not loaded from any file) -- there
    is no filename to recover here, unlike the missing-file case above.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

field = numpy.array([0.0, 0.5, 1.0, 0.5, 0.0])
v = rft.Volume()
sol = rft.Static_Magnetic_FieldMap_1d(field, 0.1)
sol.set_name("SOLFM")
sol.set_aperture(0.05, 0.05, "circular")
v.add(sol, 0, 0, 0.0, 0, 0, 0)
"""
    )
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq(1, len(e))
    pkeq("SOLENOID", e[0].type)
    pkeq("fieldMap", e[0].fieldSource)
    pkeq("", e[0].fieldMapFile)
    # real data, not a stub -- its length is still trustworthy even
    # though there's no file to name here
    pkeq(0.4, round(e[0].l, 6))
    pkeq(1, len(warnings))


def test_fieldmap_rescale_recovered_for_cavity():
    """A CAVITY's maxField is recoverable by assuming it used "peak"
    mode -- max(abs(final_field)) always equals the original
    target_field exactly, regardless of the raw file's own peak (4.0
    here, deliberately not 1.0 -- see
    rftrack_import_recorder._resolve_rescale()'s docstring for why that
    distinction matters).
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

field_data = numpy.loadtxt("gun.dat")
s = field_data[:, 0]
step = (s.max() - s.min()) / (len(s) - 1)
length = s.max() - s.min()
field = field_data[:, 1] / numpy.max(numpy.abs(field_data[:, 1])) * 15e6
v = rft.Volume()
gun = rft.RF_FieldMap_1d(field, step, length, 1.3e9, 1)
gun.set_name("GUN")
gun.set_aperture(0.05, 0.05, "circular")
v.add(gun, 0, 0, 0.0, 0, 0, 0)
""",
        data_files={"gun.dat": "0.0 0.0\n0.25 2.0\n0.5 4.0\n0.75 2.0\n1.0 0.0\n"},
    )
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq(1, len(e))
    pkeq("CAVITY", e[0].type)
    pkeq("peak", e[0].rescaleMode)
    pkeq(15.0, e[0].maxField)
    pkeq(1, e[0].scaleFactor)
    pkeq([], warnings)


def test_fieldmap_rescale_recovered_for_solenoid():
    """A SOLENOID's scaleFactor is recoverable by assuming it used
    "factor" mode -- final_field[i]/raw_field[i] always equals the
    original scale_factor exactly, for any nonzero raw point.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

field_data = numpy.loadtxt("sol.dat")
s = field_data[:, 0]
step = (s.max() - s.min()) / (len(s) - 1)
field = field_data[:, 1] * 0.0003
v = rft.Volume()
sol = rft.Static_Magnetic_FieldMap_1d(field, step)
sol.set_name("SOL")
sol.set_aperture(0.05, 0.05, "circular")
v.add(sol, 0, 0, 0.0, 0, 0, 0)
""",
        data_files={"sol.dat": "0.0 0.0\n0.25 2.0\n0.5 4.0\n0.75 2.0\n1.0 0.0\n"},
    )
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq(1, len(e))
    pkeq("SOLENOID", e[0].type)
    pkeq("factor", e[0].rescaleMode)
    pkeq(0.0003, round(e[0].scaleFactor, 10))
    pkeq(0, e[0].maxField)
    pkeq([], warnings)


def test_lattice_append_is_sequential():
    """Lattice.append(el) takes no position/offset args at all -- unlike
    Volume.add, each element's elemedge has to be reconstructed as a
    running total of the previous elements' lengths.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

v = rft.Lattice()
d1 = rft.Drift(1.5)
d1.set_name("D1")
d1.set_aperture(0.02, 0.02, "circular")
v.append(d1)
d2 = rft.Drift(0.5)
d2.set_name("D2")
d2.set_aperture(0.02, 0.02, "circular")
v.append(d2)
"""
    )
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq("relative", element_position)
    pkeq([], warnings)
    pkeq(0, e[0].elemedge)
    pkeq(1.5, e[1].elemedge)


def test_multiple_volumes_rejected():
    """A script that builds a whole second Volume -- e.g. a rough build
    to autophase against, then rebuilds with the computed phases
    before ever tracking anything for real, a real pattern an actual
    AWA lattice-design notebook uses -- is unsupported outright: there's
    no reliable way to tell which one the user actually wants a sim
    built from, so this must raise rather than silently guess (e.g. by
    picking whichever one happened to build last).
    """
    from pykern.pkunit import pkexcept
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

v1 = rft.Volume()
v1.add(rft.Drift(1.0), 0, 0, 0, 0, 0, 0)

v2 = rft.Volume()
q = rft.Quadrupole(0.2, 3.0)
q.set_name("Q1")
q.set_aperture(0.02, 0.02, "circular")
v2.add(q, 0, 0, 0, 0, 0, 0)
"""
    )
    with pkexcept("2 separate Volume"):
        rftrack_import_mapper.map_elements(res.calls)


def test_settings_autophase_does_not_block_space_charge():
    """Regression test: a real generated script's main() calls
    autophase(volume) *before* apply_space_charge(volume) -- since
    Volume.autophase() used to raise TrackingSkipped immediately (the
    same as track()), that ordering meant apply_space_charge() (and
    everything else between autophase() and track()) never ran at all,
    silently losing the space-charge settings on any script that uses
    both together. autophase()/btrack() must be no-ops that let the
    rest of the script keep running, not abort it the way track() does.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

v = rft.Volume()
v.add(rft.Drift(1.5), 0, 0, 0, 0, 0, 0)
v.set_s0(0)
v.set_s1(1.5)

p0 = rft.Bunch6dT(
    numpy.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.511, -1.0, 1.0, 0.0]])
)
v.unset_t0()
v.autophase(p0)

v.sc_dt_mm = 3.0
sc = rft.SpaceCharge_PIC_FreeSpace(8, 8, 16)
sc.set_smooth(0.5)
sc.set_mirror(0.0)
rft.cvar.SC_engine = sc

b = rft.Bunch6dT(numpy.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.511, -1.0, 1.0, 0.0]]))
tracked = v.track(b)
"""
    )
    pkeq("ok", res.status)
    settings = rftrack_import_mapper.map_settings(res.calls)
    pkeq("1", settings.autophase)
    pkeq("pic", settings.spaceCharge)
    pkeq(8, settings.scGridNx)
    pkeq(0.5, settings.scSmooth)
    pkeq(0.0, settings.scMirror)
    pkeq(3.0, settings.scDtMm)


def test_settings_none():
    """No Volume.set_s0()/set_s1() recorded at all (e.g. a bunchReport-
    only script, which never builds a beamline) -- nothing to map.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

g = rft.Bunch6dT_Generator()
g.species = "electron"
p0 = rft.Bunch6dT(g, 100)
"""
    )
    pkeq(None, rftrack_import_mapper.map_settings(res.calls))


def test_settings_p2p_space_charge():
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

v = rft.Volume()
v.add(rft.Drift(1.5), 0, 0, 0, 0, 0, 0)
v.set_s0(0)
v.set_s1(1.5)
rft.cvar.SC_engine = rft.SpaceCharge_P2P()
"""
    )
    settings = rftrack_import_mapper.map_settings(res.calls)
    pkeq("p2p", settings.spaceCharge)
    pkeq("0", settings.autophase)
    pkeq(0, settings.trackingS0)
    pkeq(1.5, settings.trackingS1)
