"""RF-Track execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import code_variable, template_common
import beamphysics
import copy
import lume_rftrack.utils
import math
import numpy
import pykern.pkio
import re
import scipy.constants
import scipy.spatial.transform
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice
import sirepo.template.madx_converter
import sirepo.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_AXIS_LABELS = PKDict(
    x="x [m]",
    xp="x' [rad]",
    y="y [m]",
    yp="y' [rad]",
    z="z [m]",
    t="t [s]",
    Px="Px [eV/c]",
    Py="Py [eV/c]",
    Pz="Pz [eV/c]",
    P="P [eV/c]",
    E="E [eV]",
    K="K [eV]",
)

# a Volume places every element on one straight z axis, which a bend turns
# the beam away from, so these need a Lattice
_BEND_TYPES = frozenset(("RBEND", "SBEND"))

_BPMS_FILE = "bpms.npy"

# RF_Track Bunch6dT_Generator momentum distribution for a Cathode Emission
# beam, which is not a user setting: a Fermi-Dirac ("fd_300") spread
_CATHODE_DIST_PZ = "fd_300"

# beam.laserTransverseProfile -> Bunch6dT_Generator (dist_x, dist_y). A
# radially uniform spot ("r") ignores dist_y.
_CATHODE_TRANSVERSE_DIST = PKDict(
    gaussian=("g", "g"),
    r=("r", "g"),
)

# RF_Track Bunch6dT_Generator.species values, keyed by our BeamParticle enum
_CATHODE_SPECIES = PKDict(
    electron="electrons",
    positron="positrons",
    proton="protons",
)

_FINAL_PARTICLES_FILE = "final_particles.npy"

_INITIAL_PARTICLES_FILE = "initial_particles.npy"

_NONE = "None"

# lume_rftrack "pic" space-charge setting -> its simulationSettings field (a tuple
# of fields for the grid), in the order the generated SETTINGS lists them;
# used both to generate the script and to import an archive
_PIC_SPACE_CHARGE_FIELDS = PKDict(
    dt_mm="scDtMm",
    grid=("scGridNx", "scGridNy", "scGridNz"),
    mirror_m="scMirror",
    smooth="scSmooth",
)

# lume_rftrack archive element class, as
# `lume_rftrack.archive.constructor_class()` names it (a _CINT field map is
# its base class, interpolated cubically) -> this app's element type.
# Others, e.g. Pillbox_Cavity (an analytic CAVITY is an RF_FieldMap_1d),
# Multipole or TW_Structure, can't be imported.
_LUME_RFTRACK_CLASS_TO_TYPE = PKDict(
    Bpm="BPM",
    Coil="COIL",
    Corrector="CORRECTOR",
    Drift="DRIFT",
    Quadrupole="QUADRUPOLE",
    RF_FieldMap_1d="CAVITY",
    RF_FieldMap_2d="CAVITY",
    SBend="SBEND",
    Screen="SCREEN",
    Sextupole="SEXTUPOLE",
    Solenoid="SOLENOID",
    Static_Magnetic_FieldMap_1d="SOLENOID",
)

_SCREEN_FILE = "screen-{}.npy"

_STATS_FILE = "stats.npy"

_STAT_LABELS = PKDict(
    s="s [m]",
    beta_x="beta_x [m]",
    beta_y="beta_y [m]",
    alpha_x="alpha_x",
    alpha_y="alpha_y",
    emitt_x="emitt_x [m*rad]",
    emitt_y="emitt_y [m*rad]",
    emitt_4d="emitt_4d [m*rad]",
    beta_z="beta_z [m]",
    alpha_z="alpha_z",
    emitt_z="emitt_z [m*rad]",
    sigma_x="sigma_x [m]",
    sigma_y="sigma_y [m]",
    sigma_z="sigma_z [m]",
    sigma_Pz="sigma_Pz [eV/c]",
    sigma_E="sigma_E [eV]",
    disp_x="disp_x [m]",
    disp_y="disp_y [m]",
    disp_px="disp_px [rad]",
    disp_py="disp_py [rad]",
    mean_x="mean_x [m]",
    mean_y="mean_y [m]",
    mean_Px="mean_Px [eV/c]",
    mean_Py="mean_Py [eV/c]",
    mean_K="mean_K [eV]",
    mean_E="mean_E [eV]",
    mean_P="mean_P [eV/c]",
    rmax="rmax [m]",
    rmax90="rmax90 [m]",
    rmax99="rmax99 [m]",
    **{"rmax99.9": "rmax99.9 [m]"},
    N="N",
    Ez="Ez [V/m]",
    Bz="Bz [T]",
)

#: RF_Track's own verbosity=1 tracking-progress line (see
#: parameters.py.jinja's `v.verbosity`), e.g.
#: "info: tracking in progress, t = 500000.0 mm/c" -- written to run.log
#: with ANSI "clear line" escapes between updates, not plain newlines,
#: but those don't interfere with finding this substring anywhere in it
_VERBOSITY_T_RE = re.compile(r"t = ([0-9.eE+-]+) mm/c")


class RftrackMadxConverter(sirepo.template.madx_converter.MadxConverter):
    """MAD-X to RF-Track: the lattice becomes a single flattened,
    sequential (Lattice) beamline. RF-Track to MAD-X: a Sequential
    (Lattice) simulation only, field maps become drifts.
    """

    # MadxConverter's settings, see MadxConverter
    _DIPEDGE_BENDS = ("SBEND",)
    _DOWNCASE_VARIABLES = True
    _ELEMENT_POSITION = "relative"
    _THICKEN_THIN_CAVITIES = True

    _DIPEDGE_FIELDS = PKDict(
        entrance=PKDict(e1="e1", fint="fint"), exit=PKDict(e1="e2")
    )
    # MAD-X's dispersion, with respect to PT as RF-Track's
    _DISP_FIELDS = PKDict(dpx="disp_px", dpy="disp_py", dx="disp_x", dy="disp_y")
    # RF-Track's named particles, the same in MAD-X
    _PARTICLE_MAP = PKDict({p: p for p in SCHEMA.constants.particleMassAndCharge})
    _ELEMENTS = PKDict(
        BPM=["MONITOR", "l"],
        CAVITY=["RFCAVITY", "l"],
        CORRECTOR=["KICKER", "l"],
        DRIFT=["DRIFT", "l"],
        QUADRUPOLE=["QUADRUPOLE", "l", "k1", "rz=tilt"],
        RBEND=["RBEND", "l", "angle", "rz=tilt"],
        SBEND=["SBEND", "l", "angle", "e1", "e2", "k1", "hgap", "fint", "rz=tilt"],
        SCREEN=["MARKER"],
        SEXTUPOLE=["SEXTUPOLE", "l", "k2", "rz=tilt"],
        SOLENOID=["SOLENOID", "l"],
    )
    _FROM_MADX = PKDict(
        COLLIMATOR="DRIFT",
        # merged into the SBEND beside it, see _merge_dipedges()
        DIPEDGE=None,
        DRIFT="DRIFT",
        ECOLLIMATOR="DRIFT",
        HKICKER="CORRECTOR",
        HMONITOR="BPM",
        INSTRUMENT="DRIFT",
        KICKER="CORRECTOR",
        # zero length drifts without an aperture are removed
        MARKER="DRIFT",
        MONITOR="BPM",
        PLACEHOLDER="DRIFT",
        QUADRUPOLE="QUADRUPOLE",
        RBEND="RBEND",
        RCOLLIMATOR="DRIFT",
        RFCAVITY="CAVITY",
        SBEND="SBEND",
        SEXTUPOLE="SEXTUPOLE",
        SOLENOID="SOLENOID",
        VKICKER="CORRECTOR",
        VMONITOR="BPM",
    )

    def __init__(self, qcall=None, **kwargs):
        super().__init__(SIM_TYPE, qcall=qcall, **kwargs)

    def _beam_to_madx(self, data, madx):
        b = data.models.beam
        # MeV to GeV
        r = PKDict(
            particle=self._particle_to_madx(b.particle),
            mass=self._val(b.mass) * 1e-3,
            charge=self._val(b.charge),
            pc=self._val(b.pc) * 1e-3,
        )
        if b.distributionType != "twiss":
            return self._beam_for_madx(reference=r)
        bg = self._val(b.pc) / self._val(b.mass)
        # a Lattice is a line, its twiss starts with the beam's
        return self._beam_for_madx(
            reference=r,
            distribution=PKDict(
                # normalized [mm-mrad] to geometric [m]
                ex=self._val(b.emit_x) * 1e-6 / bg,
                ey=self._val(b.emit_y) * 1e-6 / bg,
                # mm/c to m, sigma dE / (P c) [permille] to sigma E / E
                sigt=self._val(b.sigma_t) * 1e-3,
                sige=self._val(b.sigma_pt) * self.__beta * 1e-3,
                **{
                    f: self._val(b[f])
                    for f in sirepo.template.madx_converter.BEAM_TWISS_VARS
                },
                **{f: b[d] for f, d in self._DISP_FIELDS.items() if self._val(b[d])},
            ),
            npart=self._val(b.charge_nC)
            * 1e-9
            / scipy.constants.e
            / abs(self._val(b.charge)),
            particle_count=self._val(b.np),
        )

    def _element_handlers(self):
        return PKDict(
            from_madx=PKDict(
                ECOLLIMATOR=self._from_madx_ecollimator,
                HKICKER=self._from_madx_hkicker,
                KICKER=self._from_madx_kicker,
                QUADRUPOLE=self._from_madx_quadrupole,
                RCOLLIMATOR=self._from_madx_ecollimator,
                RFCAVITY=self._from_madx_rfcavity,
                SEXTUPOLE=self._from_madx_sextupole,
                SOLENOID=self._from_madx_solenoid,
                VKICKER=self._from_madx_vkicker,
            ),
            to_madx=PKDict(
                CAVITY=self._to_madx_cavity,
                CORRECTOR=self._to_madx_corrector,
                QUADRUPOLE=self._to_madx_quadrupole,
                SEXTUPOLE=self._to_madx_sextupole,
                SOLENOID=self._to_madx_solenoid,
            ),
        )

    def _fixup_element(self, element_in, element_out):
        super()._fixup_element(element_in, element_out)
        if self.from_class.sim_type() == SIM_TYPE:
            self.__fixup_to_madx(element_in, element_out)
        elif element_in.type not in ("ECOLLIMATOR", "RCOLLIMATOR"):
            # a collimator's own size, see _from_madx_ecollimator()
            a = self._aperture(element_in)
            if a:
                element_out.apertureShape = (
                    "rectangular" if a.apertype == "rectangle" else "circular"
                )
                element_out.aperture_x = a.x
                element_out.aperture_y = a.y

    def _fixup_from_madx(self, madx, data, beam):
        self.__flatten_beamline(madx, data)
        self.__copy_beam(data, beam)
        if any(e.type == "CAVITY" for e in data.models.elements):
            data.models.simulationSettings.autophase = "1"
        sirepo.template.lattice.LatticeUtil(data, SCHEMA).sort_elements_and_beamlines()

    def _from_madx_ecollimator(self, element_in, element_out):
        element_out.aperture_x = element_in.xsize
        element_out.aperture_y = element_in.ysize
        if self._val(element_out.aperture_x):
            element_out.apertureShape = (
                "rectangular" if element_in.type == "RCOLLIMATOR" else "circular"
            )

    def _from_madx_hkicker(self, element_in, element_out):
        self.__corrector(element_out, h=element_in.kick)

    def _from_madx_kicker(self, element_in, element_out):
        self.__corrector(element_out, h=element_in.hkick, v=element_in.vkick)

    def _from_madx_quadrupole(self, element_in, element_out):
        element_out.strengthType = "k1"

    def _from_madx_rfcavity(self, element_in, element_out):
        l = self._val(element_in.l)
        f = self._val(element_in.freq) * 1e6
        if not l or not f:
            pkdlog("dropping zero length or frequency RFCAVITY: {}", element_in.name)
            element_out.type = "DRIFT"
            element_out.l = l
            return
        element_out.fieldSource = "analytic"
        element_out.frequency = f
        # autophased RF-Track's phase is the offset from crest
        element_out.phase = 360 * self._crest_offset(element_in.lag)
        w = scipy.constants.c / (2 * f)
        if l < w / 2:
            # the generated script's single gap, sin^2(pi z / l)
            element_out.gradient = self._val(element_in.volt) / self._rf_gap_gain(
                l, f, self.particle_energy.beta
            )
            return
        # the generated script's pi-mode structure is a whole number of
        # half wavelength cells, gaining gradient * length / 2 on crest
        n = round(l / w)
        if abs(l / w - n) > 1e-3:
            n = int(l / w)
            if n:
                # the rest of the length as drifts on either side
                element_out.l = n * w
                d = PKDict(
                    name=f"{element_in.name}_D", type="DRIFT", l=(l - element_out.l) / 2
                )
                self._add_inserts(element_out._id, before=[d], after=[d])
        if not n:
            n = 1
            pkdlog(
                "RFCAVITY={} l={} is shorter than one cell, lengthened to {}",
                element_in.name,
                l,
                w,
            )
        element_out.gradient = 2 * self._val(element_in.volt) / (n * w)

    def _from_madx_sextupole(self, element_in, element_out):
        element_out.strengthType = "k2"

    def _from_madx_solenoid(self, element_in, element_out):
        b, q = self.__brho_and_sign()
        element_out.b_field = self._val(element_in.ks) * b * q

    def _from_madx_vkicker(self, element_in, element_out):
        self.__corrector(element_out, v=element_in.kick)

    def _init_to_madx(self, data):
        if data.models.simulation.elementPosition != "relative":
            raise sirepo.util.UserAlert(
                "Only a Sequential (Lattice) simulation can be converted",
                "rftrack elementPosition={} to MAD-X",
                data.models.simulation.elementPosition,
            )
        b = data.models.beam
        self.__autophase = data.models.simulationSettings.autophase == "1"
        # v / c, for _rf_gap_gain()
        self.__beta = self._val(b.pc) / math.hypot(self._val(b.pc), self._val(b.mass))
        # MeV/c to T*m
        self.__brho = (
            self._val(b.pc) * 1e6 / scipy.constants.c / abs(self._val(b.charge))
        )
        self.__charge = 1 if self._val(b.charge) > 0 else -1

    def _to_madx_cavity(self, element_in, element_out):
        if self.__is_field_map(element_in):
            return
        f = self._val(element_in.frequency)
        l = self._val(element_in.l)
        w = scipy.constants.c / (2 * f)
        if l < w / 2:
            # the generated script's single gap
            element_out.volt = self._val(element_in.gradient) * self._rf_gap_gain(
                l, f, self.__beta
            )
        else:
            # the generated script's pi-mode structure of whole half
            # wavelength cells gains gradient * length / 2 on crest
            element_out.volt = self._val(element_in.gradient) * round(l / w) * w / 2
        element_out.freq = f * 1e-6
        element_out.lag = self._lag_from_crest_offset(self._val(element_in.phase) / 360)
        if not self.__autophase:
            pkdlog(
                "CAVITY={} phase is absolute without autophase, lag assumes it's from crest",
                element_in.name,
            )

    def _to_madx_corrector(self, element_in, element_out):
        # integrated field [T*mm] to kick [rad], see __corrector()
        q = self.__charge
        element_out.hkick = self._val(element_in.h_kick) / (1e3 * self.__brho * q)
        element_out.vkick = -self._val(element_in.v_kick) / (1e3 * self.__brho * q)

    def _to_madx_quadrupole(self, element_in, element_out):
        if element_in.strengthType != "k1":
            element_out.k1 = self._val(element_in.gradient) / (
                self.__brho * self.__charge
            )

    def _to_madx_sextupole(self, element_in, element_out):
        if element_in.strengthType != "k2":
            element_out.k2 = self._val(element_in.gradient) / (
                self.__brho * self.__charge
            )

    def _to_madx_solenoid(self, element_in, element_out):
        if self.__is_field_map(element_in):
            return
        element_out.ks = self._val(element_in.b_field) / (self.__brho * self.__charge)

    def __beamline_elements(self, data, beamline_id, is_reversed=False):
        """The element ids of a beamline and its sub-beamlines, in order: a
        reversed beamline's in reverse, each sub-beamline reversed again
        when it is itself reversed"""
        b = PKDict({x.id: x for x in data.models.beamlines})
        res = []
        for i in (reversed if is_reversed else iter)(b[beamline_id]["items"]):
            if abs(i) in b:
                res.extend(
                    self.__beamline_elements(data, abs(i), (i < 0) != is_reversed)
                )
            else:
                res.append(abs(i))
        return res

    def __brho_and_sign(self):
        """MAD-X beam's rigidity [T*m] and charge's sign: RF-Track's
        strengths are relative to the signed P/Q"""
        return self.particle_energy.brho, 1 if self.beam.charge > 0 else -1

    def __copy_beam(self, data, beam):
        b = data.models.beam
        e = self.particle_energy
        b.particle = self._particle_from_madx(self.beam.particle) or "other"
        b.mass = self.beam.mass * 1e3
        b.charge = self.beam.charge
        b.pc = e.pc * 1e3
        for dim in ("x", "y"):
            if beam[f"e{dim}"] is not None:
                # geometric [m] to normalized [mm-mrad]
                b[f"emit_{dim}"] = self._val(beam[f"e{dim}"]) * e.beta * e.gamma * 1e6
        b.update(beam.twiss)
        for f, v in beam.dispersion.items():
            b[self._DISP_FIELDS[f]] = v
        if beam.sigt is not None:
            # m to mm/c
            b.sigma_t = self._val(beam.sigt) * 1e3
        # sigma E / E to RF-Track's sigma dE / (P c) [permille]
        b.sigma_pt = self._val(beam.sige) / e.beta * 1e3
        if beam.npart:
            b.charge_nC = beam.npart * abs(b.charge) * scipy.constants.e * 1e9
        if beam.particle_count:
            b.np = beam.particle_count
        b.distributionType = "twiss"

    def __corrector(self, element_out, h=None, v=None):
        # kick [rad] to integrated field [T*mm], signs found by tracking
        b, q = self.__brho_and_sign()
        if h is not None:
            element_out.h_kick = self._val(h) * 1e3 * b * q
        if v is not None:
            element_out.v_kick = -self._val(v) * 1e3 * b * q

    def __fixup_to_madx(self, element_in, element_out):
        """Field maps as drifts, misalignments and apertures, before the
        element type's handler"""
        t = element_in.type
        if self.__is_field_map(element_in):
            pkdlog(
                "{}={} field map has no MAD-X equivalent, replaced by a DRIFT",
                t,
                element_in.name,
            )
            element_out.type = "DRIFT"
            element_out.l = element_in.l
            return
        if any(
            self._val(element_in.get(f, 0)) for f in ("dx", "dy", "dz", "rx", "ry")
        ) or (self._val(element_in.get("rz", 0)) and "tilt" not in element_out):
            pkdlog("{}={} misalignment has no MAD-X equivalent", t, element_in.name)
        if element_in.get(
            "apertureShape", "none"
        ) != "none" and "_APERTURE_ELEMENT" in (
            self.to_class.schema().model[element_out.type].get("_super", [])
        ):
            if element_in.apertureShape == "circular":
                element_out.apertype = "circle"
                element_out.aperture = self._array_text(
                    [self._val(element_in.aperture_x)]
                )
            else:
                element_out.apertype = "rectangle"
                element_out.aperture = self._array_text(
                    [
                        self._val(element_in.aperture_x),
                        self._val(element_in.aperture_y),
                    ]
                )

    def __flatten_beamline(self, madx, data):
        """The used beamline as one beamline of its elements in sequence,
        see __used_beamline()"""
        b = self.__used_beamline(madx, data)
        s = self.__sequential_items(data, self.__beamline_elements(data, b.id))
        data.models.beamlines = [PKDict(id=b.id, name=b.name, **s)]
        data.models.elements = [e for e in data.models.elements if e._id in s["items"]]
        data.models.simulation.activeBeamlineId = (
            data.models.simulation.visualizationBeamlineId
        ) = b.id

    def __is_field_map(self, element):
        return (
            element.type in ("CAVITY", "SOLENOID") and element.fieldSource != "analytic"
        )

    def __sequential_items(self, data, element_ids):
        """`element_ids` placed one after another, without zero length drifts
        (a zero length aperture, ex. a COLLIMATOR, stays)

        Returns:
            PKDict: items and positions, see __flatten_beamline()
        """
        e = PKDict({x._id: x for x in data.models.elements})
        v = code_var(data.models.rpnVariables)
        res = PKDict(items=[], positions=[], s=0)
        for i in element_ids:
            l = v.eval_var_with_assert(e[i].l)
            if (
                e[i].type == "DRIFT"
                and l == 0
                and e[i].get("apertureShape", "none") == "none"
            ):
                continue
            res["items"].append(i)
            res.positions.append(PKDict(elemedge=res.s))
            res.s += l
        res.pkdel("s")
        return res

    def __used_beamline(self, madx, data):
        """The beamline MAD-X's "use" names, else the last one no other
        beamline contains"""
        if any(c._type == "use" for c in madx.models.commands):
            return next(
                b
                for b in data.models.beamlines
                if b.id == data.models.simulation.get("visualizationBeamlineId")
            )
        u = set(abs(i) for b in data.models.beamlines for i in b["items"])
        return [b for b in data.models.beamlines if b.id not in u][-1]


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=_rough_percent_complete(run_dir),
            frameCount=0,
        )
    r = _output_info(_read_data(run_dir), run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1 if len(r) else 0,
        reports=r,
    )


def build_imported_data(archive, name, qcall):
    """Build the full imported sirepo data from `archive`, a lume_rftrack
    HDF5 archive as returned by `lume_rftrack.archive.read_archive()`.
    The bunch is written to a new lib file for a "fromFile" beam
    (`_write_distribution_lib_file`), and each field map to a new lib
    file (`_write_field_map_lib_file`).

    Every element is checked first (`_lume_rftrack_import_errors`), so
    an archive that can't be imported writes no lib files. Identical
    elements (same name and fields, e.g. a FODO cell's repeated
    quadrupoles) become one element, used once per position; a name
    used by different elements, or none, gets a unique one, since the
    lattice editor requires them. A Lattice's element offsets become
    each element's misalignment, a Volume's positions its dx, dy and
    beamline position, and a Volume's tracking range and integrator its
    simulationSettings (a non-finite step keeps the default).

    Each cavity's `phase` is simply its archived `phid`, nothing folded
    in. An autophased archive turns on Autophase, so the generated script
    phases the cavities again. Space charge has no per-element signal to
    derive from, so it can only be restored from this archived setting.
    An SBEND is built with the beam's rigidity, so `beam.pc` is the
    bends' archived rigidity.

    Called from `sirepo.sim_data.rftrack.SimData.prepare_import_file_args`
    -- on the server, not from `stateful_compute_import_file` below (the
    job agent), since writing lib files needs `qcall`, and only the server
    has one.

    Raises:
        sirepo.util.UserAlert: every reason `archive` can't be imported
    """
    import json

    err = _lume_rftrack_import_errors(archive)
    if err:
        raise sirepo.util.UserAlert(
            "The archive can't be imported: " + "; ".join(err) + ".",
            "import errors={}",
            err,
        )
    res = simulation_db.default_data(SIM_TYPE)
    res.models.simulation.name = name
    # RF_Track's Lattice.track() has no Bunch6dT support at all, so a
    # Bunch6dT-bunch archive is always a Volume, but a Bunch6d-bunch
    # archive could be either
    is_volume = archive.beamline_class == "Volume"
    res.models.simulation.elementPosition = "absolute" if is_volume else "relative"
    els = []
    # an element's fields as json, before naming -> its element
    by_fields = {}
    names = set()
    items = []
    positions = []
    elemedge = 0.0
    # shared across every element below: see _write_field_map_lib_file()
    field_map_cache = {}
    for i, e in enumerate(archive.elements):
        el = _lume_rftrack_element_to_sirepo(e, qcall, field_map_cache)
        if is_volume:
            el.dx = float(e.x)
            el.dy = float(e.y)
        else:
            # Lattice.get_elements_offsets(): the entrance's offset [mm] and
            # rotation as a quaternion (w, x, y, z), which is extrinsic
            # rotations about x (pitch), y (yaw), z (roll) in that order,
            # as the generated script's Lattice.append() takes them
            o = archive.elements_offsets[i]
            el.dx, el.dy, el.dz = (float(x) / 1000.0 for x in o[:3])
            el.rx, el.ry, el.rz = (
                float(x)
                for x in scipy.spatial.transform.Rotation.from_quat(
                    [o[4], o[5], o[6], o[3]]
                ).as_euler("xyz")
            )
        k = json.dumps(el, sort_keys=True)
        if k in by_fields:
            el = by_fields[k]
        else:
            if not el.name:
                el.name = _unique_name(el.type[0], names)
            elif el.name in names:
                el.name = _unique_name(el.name + "-", names)
            names.add(el.name)
            el._id = len(els) + 1
            els.append(el)
            by_fields[k] = el
        items.append(el._id)
        if is_volume:
            # a Volume element's own absolute position: Volume elements
            # can be at arbitrary, even overlapping z (e.g. a gun cavity
            # and a bucking solenoid), so packing them end to end would
            # be wrong
            positions.append(PKDict(elemedge=float(e.z)))
        else:
            positions.append(PKDict(elemedge=elemedge))
            elemedge += el.l
    res.models.elements = els
    res.models.beamlines = [
        PKDict(id=len(els) + 1, name="Beamline1", items=items, positions=positions)
    ]
    # only one beamline is ever built here, so it's both the active
    # (Lattice editor selection) and visualization (report) beamline --
    # same pairing LatticeParser._set_default_beamline() uses for
    # command-based (Elegant/MAD-X) imports, which this HDF5 import
    # doesn't go through.
    res.models.simulation.activeBeamlineId = (
        res.models.simulation.visualizationBeamlineId
    ) = (len(els) + 1)
    res.models.beam = _lume_rftrack_bunch_to_sirepo(
        archive.bunch_type,
        archive.particle_group,
        _write_distribution_lib_file(archive.particle_group, name, qcall),
    )
    b = [e for e in archive.elements if e["class"] == "SBend"]
    if b:
        res.models.beam.pc = abs(
            float(b[0].attributes.P_over_Q) * res.models.beam.charge
        )
    s = res.models.simulationSettings
    if archive.autophase:
        s.autophase = "1"
    if not is_volume:
        # the archived elements' own space-charge kicks
        s.scLatticeNsteps = 0
    if is_volume:
        s.autoTrackingRange = "0"
        s.trackingS0 = float(archive.s0)
        s.trackingS1 = float(archive.s1)
        s.odeintAlgorithm = str(archive.integrator.odeint_algorithm)
        s.odeintEpsabs = float(archive.integrator.odeint_epsabs)
        s.odeintEpsrel = float(archive.integrator.odeint_epsrel)
        for f, k in (("volumeDtMm", "dt_mm"), ("volumeTtDtMm", "tt_dt_mm")):
            if numpy.isfinite(archive.integrator[k]):
                s[f] = float(archive.integrator[k])
        if numpy.isfinite(archive.integrator.t_max_mm):
            s.volumeTMaxMm = float(archive.integrator.t_max_mm)
    c = archive.space_charge
    if c:
        s.spaceCharge = c.kind
        if c.kind == "pic":
            for k, f in _PIC_SPACE_CHARGE_FIELDS.items():
                if isinstance(f, tuple):
                    for x, n in zip(f, c[k]):
                        s[x] = int(n)
                else:
                    s[f] = float(c[k])
    sirepo.template.lattice.LatticeUtil(res, SCHEMA).sort_elements_and_beamlines()
    return res


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def get_data_file(run_dir, model, frame, options):
    if "bunchReport" in model:
        fn = _INITIAL_PARTICLES_FILE
    elif frame < 0:
        return template_common.text_data_file(template_common.RUN_LOG, run_dir)
    else:
        fn = _file_name_for_element_animation(
            run_dir,
            model,
            simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)),
        )
    if options and options.get("suffix") == "openpmd":
        return _openpmd_job_cmd_file(run_dir, fn)
    return fn


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def prepare_sequential_output_file(run_dir, data):
    report = data["report"]
    if "bunchReport" in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_sequential_report_data(data, run_dir)
            except IOError:
                # the output file isn't readable
                pass


def python_source_for_model(data, model, qcall, **kwargs):
    if model == "madx":
        return RftrackMadxConverter(qcall=qcall).to_madx_text(data)
    return _generate_parameters_file(data)


def save_sequential_report_data(data, run_dir):
    template_common.write_sequential_result(
        _phase_space_plot(
            data.models[data.report],
            numpy.load(str(run_dir.join(_INITIAL_PARTICLES_FILE))),
        ),
        run_dir=run_dir,
    )


def sim_frame(frame_args):
    # elementAnimations (SCREEN output)
    return _phase_space_plot(
        frame_args,
        numpy.load(
            str(
                frame_args.run_dir.join(
                    _file_name_for_element_animation(
                        frame_args.run_dir, frame_args.frameReport, frame_args.sim_in
                    )
                )
            )
        ),
    )


def sim_frame_bpmAnimation(frame_args):
    c = lume_rftrack.utils.BPM_COLUMNS.index
    return PKDict(
        rows=[
            [
                f"{r[c('s')]:.3f}",
                f"{r[c('charge')]:.3e}",
                f"{r[c('x')]:.4f}",
                f"{r[c('y')]:.4f}",
            ]
            for r in numpy.load(str(frame_args.run_dir.join(_BPMS_FILE)))
        ],
    )


def sim_frame_stat2Animation(frame_args):
    return _stat_animation_plot(frame_args)


def sim_frame_statAnimation(frame_args):
    return _stat_animation_plot(frame_args)


def stat_columns():
    return [_NONE] + sorted(lume_rftrack.utils.STAT_COLUMNS, key=str.lower)


def stateful_compute_convert_lattice(data, **kwargs):
    return PKDict(
        imported_data=sirepo.template.madx_converter.convert_lattice(
            data, data.args.toSimType
        )
    )


def stateful_compute_import_file(data, **kwargs):
    """Convert a MAD-X file. An HDF5 archive is a passthrough:
    `sirepo.sim_data.rftrack.SimData.prepare_import_file_args` already
    built the full imported data (via `build_imported_data` above), on
    the server, before this was ever called -- see that method's
    docstring for why.
    """
    if "imported_data" in data.args:
        return PKDict(imported_data=data.args.imported_data)
    if data.args.ext_lower not in (".madx", ".seq"):
        raise sirepo.util.UserAlert(
            f"invalid file={data.args.basename}, expecting .h5, .madx or .seq",
            "invalid import file extension={}",
            data.args.ext_lower,
        )
    res = RftrackMadxConverter().from_madx_text(data.args.file_as_str)
    res.models.simulation.name = data.args.purebasename
    return PKDict(imported_data=res)


def validate_file(file_type, path, sim_id, qcall):
    """Recompute `l` for every CAVITY/SOLENOID element referencing a
    field-map file that was just uploaded, since that's the one
    field-map value genuinely derivable from the file's own content:
    two numeric columns (s [m], field) for a 1D map, or (for a CAVITY's
    2D map) a SUPERFISH-style file whose first column is Z [cm].
    """
    m = re.match(r"^(CAVITY|SOLENOID)-(fieldMapFile|fieldMapFile2d)$", file_type)
    if not m:
        return None
    el_type, field = m.group(1), m.group(2)
    try:
        # numpy.loadtxt() already skips `#`-commented header lines on
        # its own, same as a SUPERFISH 2D map's two header lines
        s = numpy.loadtxt(str(path))[:, 0]
        length = s.max() - s.min()
        if field == "fieldMapFile2d":
            length /= 100  # Z is in cm, not m
    except (IndexError, ValueError):
        return (
            f"{path.basename} is not a valid field map file"
            " (expecting two numeric columns: s [m], field)"
            if field == "fieldMapFile"
            else (
                f"{path.basename} is not a valid 2D field map file"
                " (expecting a SUPERFISH-style file: two commented header"
                " lines, then rows of Z [cm], R [cm], Ez [MV/m], Er [MV/m],"
                " |E| [MV/m], H [A/m])"
            )
        )
    try:
        data = simulation_db.open_json_file(SIM_TYPE, sid=sim_id, qcall=qcall)
    except sirepo.util.SPathNotFound as e:
        # best-effort: sim_id isn't always a real, already-saved
        # simulation (e.g. a lib file uploaded ahead of any sim, as a
        # shared library entry) -- nothing to update in that case, not
        # an error worth failing the upload itself over
        pkdlog("validate_file sim_id={} error={}", sim_id, e)
        return None
    changed = False
    for el in data.models.elements:
        if el.get("type") == el_type and el.get(field) == path.basename:
            el.l = length
            changed = True
    if changed:
        simulation_db.save_simulation_json(
            data, fixup=False, qcall=qcall, modified=True
        )
    return None


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _axis_label(name):
    return _AXIS_LABELS[name]


def _bunch_spec(dm, v):
    """Build the BUNCH data record: every value build_bunch()/autophase()/
    _build_element() (for the rigidity of RBEND, SBEND and k1/k2
    strengths) need, keyed by the field names those generated-script
    functions reference.
    """
    beam = dm.beam
    mass, charge = _particle_mass_and_charge().get(beam.particle) or (
        beam.mass,
        beam.charge,
    )
    res = PKDict(
        charge=charge,
        mass_mev=mass,
        pc_mev=beam.pc,
        random_seed=beam.randomSeed,
    )
    if v.isCathode:
        res.update(
            c_sig_t=beam.cutoffT,
            c_sig_x=beam.cutoffX,
            c_sig_y=beam.cutoffY,
            cathode=True,
            dist_pz=_CATHODE_DIST_PZ,
            dist_x=_CATHODE_TRANSVERSE_DIST[beam.laserTransverseProfile][0],
            dist_y=_CATHODE_TRANSVERSE_DIST[beam.laserTransverseProfile][1],
            dist_z=beam.laserTemporalProfile,
            e_photon=beam.ePhoton,
            lt=beam.flatTopLength,
            noise_reduc=beam.noiseReduc == "1",
            np=beam.np,
            phi_eff=beam.phiEff,
            q_total_nc=beam.charge_nC,
            ref_clock=0,
            ref_ekin=0,
            ref_zpos=0,
            rt=beam.riseTime,
            # the generator ignores whichever of rt/lt and sig_t the
            # temporal profile doesn't use, and sig_y for a radial spot
            sig_t=beam.sigT,
            sig_x=beam.sigX,
            sig_y=beam.sigX,
            species=_CATHODE_SPECIES.get(beam.particle, "electrons"),
        )
    elif v.isFromFile:
        res.update(
            distribution_file=_SIM_DATA.lib_file_name_with_model_field(
                "beam", "distributionFile", beam.distributionFile
            ),
        )
    else:
        res.update(
            alpha_x=beam.alpha_x,
            alpha_y=beam.alpha_y,
            beta_x=beam.beta_x,
            beta_y=beam.beta_y,
            charge_nc=beam.charge_nC,
            disp_px=beam.disp_px,
            disp_py=beam.disp_py,
            disp_x=beam.disp_x,
            disp_y=beam.disp_y,
            emit_x=beam.emit_x,
            emit_y=beam.emit_y,
            np=beam.np,
            sigma_pt=beam.sigma_pt,
            sigma_t=beam.sigma_t,
        )
    return res


def _element_spec(el):
    """Build the ELEMENTS data record for one lattice element: a "kind"
    discriminator plus whatever fields the generated script's
    _build_element() and `lume_rftrack.utils.load_field_map()` need for
    that kind, and the aperture/misalignment fields every kind has.

    Returns (spec, is_cavity).
    """
    res = PKDict(
        name=el.name,
        elemedge=el.elemedge,
        aperture_shape=el.apertureShape,
        aperture_x=el.aperture_x,
        aperture_y=el.aperture_y,
        dx=el.dx,
        dy=el.dy,
        dz=el.dz,
        rx=el.rx,
        ry=el.ry,
        rz=el.rz,
    )
    is_cavity = False
    if el.type == "DRIFT":
        res.kind = "drift"
        res.l = el.l
    elif el.type == "QUADRUPOLE":
        if el.get("strengthType") == "k1":
            res.kind = "quadrupole_k1"
            res.l = el.l
            res.k1 = el.k1
        else:
            res.kind = "quadrupole_gradient"
            res.l = el.l
            res.gradient = el.gradient
    elif el.type == "SEXTUPOLE":
        res.l = el.l
        if el.strengthType == "k2":
            res.kind = "sextupole_k2"
            res.k2 = el.k2
        else:
            res.kind = "sextupole_gradient"
            res.gradient = el.gradient
    elif el.type == "RBEND":
        res.kind = "rbend"
        res.l = el.l
        res.angle = el.angle
    elif el.type == "SBEND":
        res.kind = "sbend"
        res.l = el.l
        res.angle = el.angle
        res.e1 = el.e1
        res.e2 = el.e2
        res.k1 = el.k1
        res.hgap = el.hgap
        res.fint = el.fint
    elif el.type == "SOLENOID":
        if el.get("fieldSource") == "fieldMap":
            res.kind = "solenoid_fieldmap"
            res.update(_field_map_spec(el, is_cavity=False))
        else:
            res.kind = "solenoid_analytic"
            res.l = el.l
            res.b_field = el.b_field
            res.radius = el.radius
    elif el.type == "COIL":
        res.kind = "coil"
        res.l = el.l
        res.b_field = el.b_field
        res.radius = el.radius
    elif el.type == "CORRECTOR":
        res.kind = "corrector"
        res.l = el.l
        res.h_kick = el.h_kick
        res.v_kick = el.v_kick
    elif el.type == "CAVITY":
        is_cavity = True
        if el.get("fieldSource") == "fieldMap":
            res.kind = "cavity_fieldmap"
            res.update(_field_map_spec(el, is_cavity=True))
        elif el.get("fieldSource") == "2dFieldMap":
            res.kind = "cavity_fieldmap_2d"
            res.update(_field_map_2d_spec(el))
        else:
            res.kind = "cavity_analytic"
            res.l = el.l
            res.frequency_hz = el.frequency
            res.gradient_v_per_m = el.gradient * 1e6
        res.phase_deg = float(el.phase)
    elif el.type == "SCREEN":
        res.kind = "screen"
        res.width = el.width
        res.height = el.height
    elif el.type == "BPM":
        res.kind = "bpm"
        res.l = el.l
        res.resolution = el.resolution
    else:
        raise AssertionError(f"unsupported element type={el.type}")
    return res, is_cavity


def _evaluated_data(data):
    """A copy of `data` with every RPNValue field of the elements, the beam
    and the beamline positions replaced by its evaluated float, so nothing
    else in this module sees a variable expression.
    """
    res = copy.deepcopy(data)
    cv = code_var(res.models.rpnVariables)

    def _eval(value, label):
        v, e = cv.eval_var(value)
        if e:
            raise sirepo.util.UserAlert(
                f"{label}: {e}",
                "label={} value={} err={}",
                label,
                value,
                e,
            )
        return float(v)

    def _model(m, name):
        for f, s in SCHEMA.model[name].items():
            if s[1] == "RPNValue" and m.get(f) not in (None, ""):
                m[f] = _eval(m[f], f"{m.get('name') or name} {f}")

    _model(res.models.beam, "beam")
    for e in res.models.elements:
        _model(e, e.type)
    for b in res.models.beamlines:
        for p in b.get("positions", []):
            for f in p:
                if p[f] not in (None, ""):
                    p[f] = _eval(p[f], f"{b.name} position {f}")
    return res


def _field_map_2d_spec(el):
    # no rescale_mode/scale_factor/target_field, unlike _field_map_spec():
    # a 2D (r, z) SUPERFISH-style map is already in absolute physical
    # units (MV/m), with no peak-normalize-or-multiply step applied to it
    return PKDict(
        cubic=el.fieldMapInterpolation == "cubic",
        file=_SIM_DATA.lib_file_name_with_model_field(
            "CAVITY", "fieldMapFile2d", el.fieldMapFile2d
        ),
        frequency_hz=el.frequency,
    )


def _field_map_spec(el, is_cavity):
    res = PKDict(
        cubic=el.fieldMapInterpolation == "cubic",
        file=_SIM_DATA.lib_file_name_with_model_field(
            el.type, "fieldMapFile", el.fieldMapFile
        ),
    )
    if el.get("rescaleMode") == "factor":
        res.rescale_mode = "factor"
        res.scale_factor = el.scaleFactor
    else:
        res.rescale_mode = "peak"
        res.target_field = el.maxField * 1e6 if is_cavity else el.maxField
    if is_cavity:
        res.frequency_hz = el.frequency
    return res


def _file_name_for_element_animation(run_dir, report, data):
    for info in _output_info(data, run_dir):
        if info.modelKey == report:
            return info.filename
    raise AssertionError(f"no output for frame={report}")


def _format_value(value, indent):
    """Render `value` as Python source: a dict becomes a multi-line
    PKDict(key=value, ...) call (recursively, for nested dicts/lists/
    tuples), so every value the generated script's functions use is
    visible in one of ELEMENTS/BUNCH/SETTINGS rather than injected as a
    bare literal.
    """
    if isinstance(value, dict):
        pad = " " * (indent + 4)
        return (
            "PKDict(\n"
            + "".join(
                f"{pad}{k}={_format_value(v, indent + 4)},\n" for k, v in value.items()
            )
            + " " * indent
            + ")"
        )
    if isinstance(value, (list, tuple)):
        pad = " " * (indent + 4)
        o, c = ("[", "]") if isinstance(value, list) else ("(", ")")
        return (
            o
            + "\n"
            + "".join(f"{pad}{_format_value(v, indent + 4)},\n" for v in value)
            + " " * indent
            + c
        )
    return repr(value)


def _generate_lattice(util, beamline_id, result):
    beamline = util.get_item(abs(beamline_id))
    for idx, item_id in enumerate(beamline["items"]):
        item = util.get_item(abs(item_id))
        if "type" in item:
            item = PKDict(item)
            # the beamline (not the element) is the source of truth for an
            # element's absolute position, matching how impactt reads
            # beamline.positions[idx].elemedge -- this is what lets the
            # same element in principle appear in different beamlines at
            # different positions, and is what the lattice editor's
            # "absolute" element-positioning UI edits.
            item.elemedge = beamline.positions[idx].elemedge
            result.append(item)
        else:
            # rftrack's lattice editor doesn't offer reversing a beamline
            # (SIREPO.lattice.canReverseBeamline is unset), and this
            # traversal doesn't reverse one
            if item_id < 0:
                raise AssertionError(f"reversed beamline={item.name} is not supported")
            _generate_lattice(util, item.id, result)
    return result


def _generate_parameters_file(data):
    data = _evaluated_data(data)
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    dm = data.models
    v.spaceCharge = dm.simulationSettings.spaceCharge
    v.autophase = dm.simulationSettings.autophase == "1"
    v.autophaseFromBunch = dm.simulationSettings.autophaseReference == "bunch"
    v.hasCavity = False
    # Volume and Lattice are both valid RF_Track tracking objects -- Volume
    # places every element at its own explicit (possibly overlapping)
    # position; Lattice appends elements sequentially (see
    # _sequential_elements()) and has no absolute-position concept at all.
    # This is a beamline-construction choice, not a tracking difference,
    # so it's locked at simulation creation (simulationView's watchFields)
    # rather than editable, since Volume- and Lattice-only settings (the
    # tracking range; per-element step counts vs. a continuous ODE step
    # size) aren't interchangeable once a beamline is built around one.
    v.isLattice = dm.simulation.elementPosition == "relative"
    v.isCathode = dm.beam.distributionType == "cathode"
    v.isFromFile = dm.beam.distributionType == "fromFile"
    # From File is constructed as a Bunch6dT, like Cathode, when the file
    # holds a near-rest bunch (e.g. a Cathode Emission snapshot): this
    # preserves the file's actual 3D momentum, avoiding the small-angle
    # approximation a Bunch6d's x'/y' would otherwise need (invalid when
    # Pz is comparable to the transverse momentum). For an
    # already-accelerated bunch (e.g. re-injecting a previous sim's own
    # tracked output downstream, where Pz dominates), that approximation is
    # fine, and Bunch6d is used instead since it's the only bunch type
    # Lattice.track() supports at all (see the isLattice/isBunch6dT check
    # below). fromFileNearRest is user-controlled, not auto-detected from
    # the file, so this choice is explicit rather than a heuristic guess.
    v.isBunch6dT = v.isCathode or (v.isFromFile and dm.beam.fromFileNearRest == "1")
    # an openPMD file can only name a species beamphysics knows, with its
    # mass (e.g. H- at 939.294 MeV/c^2); "other" uses the beam's own
    v.isOtherParticle = dm.beam.particle == "other"
    if v.isLattice and v.isBunch6dT:
        # Lattice.track() only accepts a Bunch6d (or the generic Beam
        # supertype) -- verified empirically, it has no Bunch6dT overload
        # at all, unlike Volume.track(), which accepts either.
        raise sirepo.util.UserAlert(
            "Sequential (Lattice) positioning does not support a Bunch6dT"
            " distribution -- switch Distribution to Twiss Parameters,"
            " uncheck From File's Near-Rest Bunch, or use Absolute (Volume)"
            " positioning.",
            "Lattice mode incompatible with Bunch6dT distribution",
        )
    v.isBunchReport = "bunchReport" in data.get("report", "")
    v.bpmsFile = _BPMS_FILE
    v.finalParticlesFile = _FINAL_PARTICLES_FILE
    v.initialParticlesFile = _INITIAL_PARTICLES_FILE
    v.screenFile = _SCREEN_FILE
    v.statsFile = _STATS_FILE

    if not v.isBunchReport:
        elements = _generate_lattice(util, util.select_beamline().id, [])
        if v.isLattice:
            elements = _sequential_elements(elements)
        else:
            b = sorted({e.name for e in elements if e.type in _BEND_TYPES})
            if b:
                raise sirepo.util.UserAlert(
                    f"Bends ({', '.join(b)}) need Relative (Lattice)"
                    " positioning: Absolute (Volume) positioning places every"
                    " element on one straight axis, which a bend turns the"
                    " beam away from.",
                    "bends={} in Volume",
                    b,
                )

        specs = []
        for e in elements:
            s, is_cavity = _element_spec(e)
            if v.isLattice:
                s.update(_integration_spec(e))
            specs.append(s)
            v.hasCavity = v.hasCavity or is_cavity
        v.elementsCode = _format_value(specs, 0)
        settings = PKDict(
            num_threads=sirepo.mpi.cfg().cores,
            space_charge=_space_charge_spec(dm.simulationSettings),
        )
        if v.isLattice:
            if dm.simulationSettings.spaceCharge != "none":
                settings.sc_lattice_nsteps = dm.simulationSettings.scLatticeNsteps
        else:
            settings.tracking_range_m = _tracking_range(dm.simulationSettings, elements)
            settings.odeint_algorithm = dm.simulationSettings.odeintAlgorithm
            settings.odeint_epsabs = dm.simulationSettings.odeintEpsabs
            settings.odeint_epsrel = dm.simulationSettings.odeintEpsrel
            settings.volume_dt_mm = dm.simulationSettings.volumeDtMm
            settings.volume_tt_dt_mm = dm.simulationSettings.volumeTtDtMm
            # 0 is RF-Track's default, no limit (infinity)
            if dm.simulationSettings.volumeTMaxMm > 0:
                settings.t_max_mm = dm.simulationSettings.volumeTMaxMm
        v.settingsCode = _format_value(settings, 0)

    v.bunchCode = _format_value(_bunch_spec(dm, v), 0)
    return res + template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )


def _infer_particle(mass_mev, charge):
    """Match (`mass_mev`, `charge`) against `_particle_mass_and_charge()`'s
    known species, returning the matching `beam.particle` value, or
    "other" if nothing matches. `mass`/`charge` are archived exactly (not
    a statistical fit, unlike the Twiss values this doesn't touch), so an
    exact-ish match is a reliable identification, not a guess.
    """
    for name, (mass, charge_e) in _particle_mass_and_charge().items():
        if numpy.isclose(mass_mev, mass, rtol=1e-6) and charge == charge_e:
            return name
    return "other"


def _integration_spec(el):
    """How a Lattice tracks through `el`: its step counts and, for an
    element whose field it integrates, the integrator. A Volume uses its
    own settings instead."""
    return PKDict(
        nsteps=el.nsteps,
        tt_nsteps=el.ttNsteps,
        sc_nsteps=el.scNsteps,
        odeint_algorithm=el.odeintAlgorithm,
        odeint_epsabs=el.odeintEpsabs,
        odeint_epsrel=el.odeintEpsrel,
    )


def _lume_rftrack_bunch_to_sirepo(bunch_type, particle_group, distribution_file):
    """Build the `beam` model for a lume_rftrack archive's bunch --
    always "fromFile": it already handles both Bunch6d and Bunch6dT (via
    fromFileNearRest), so no separate distributionType/field set is
    needed for either, unlike a Twiss-style statistical-moment summary
    (which Bunch6dT has no schema fields for at all).

    `particle`/`mass`/`charge` are still set explicitly here, not left
    to the file alone: the autophase reference particle is built from
    them, and for particle "other" build_bunch() (the generated script)
    also gives the tracked bunch this mass and charge instead of the
    file's embedded species'.
    `randomSeed` isn't in the archive at all (RF-Track's own API has no
    getter for it), so it's left for fixup_old_data()'s own
    schema-default backfill, same as every other `beam` field this
    doesn't set explicitly.
    """
    mass_mev = particle_group.mass / 1e6
    charge = particle_group.species_charge / scipy.constants.e
    return PKDict(
        particle=_infer_particle(mass_mev, charge),
        mass=mass_mev,
        charge=charge,
        distributionType="fromFile",
        distributionFile=distribution_file,
        fromFileNearRest="1" if bunch_type == "Bunch6dT" else "0",
    )


def _lume_rftrack_element_to_sirepo(e, qcall, field_map_cache):
    """The sirepo element model, without `_id`, for `e`, an element of a
    lume_rftrack archive (`read_archive()`) that
    `_lume_rftrack_import_errors()` accepted, with RF-Track's own names:
    its settable `attributes` and, for a class that needs them, its
    `constructor` arguments. A field map is written to a lib file, shared
    by every element with the same map (see `_write_field_map_lib_file`).

    archive() samples a field map without its scaling, which it restores
    with the setters: the power scaling sqrt(P_actual / P_map) and
    `scaling_factor` are a 1D map's scaleFactor, and are applied to a 2D
    map's field, which this app doesn't rescale.
    """
    import io
    import lume_rftrack.archive
    import lume_rftrack.utils

    cls = lume_rftrack.archive.constructor_class(e["class"])
    a = e.attributes
    c = e.get("constructor", PKDict())
    t = _LUME_RFTRACK_CLASS_TO_TYPE[cls]
    # schema defaults for everything the archive doesn't carry; rotations
    # and offsets are set by build_imported_data()
    res = _SIM_DATA.model_defaults(t).pkupdate(type=t, name=str(e.name))
    if e.aperture_set:
        res.apertureShape = str(e.aperture_shape)
        res.aperture_x = float(e.aperture_x)
        res.aperture_y = float(e.aperture_y)
    if "length" in a:
        res.l = float(a.length)
    for f, k in (
        ("nsteps", "nsteps"),
        ("ttNsteps", "tt_nsteps"),
        ("scNsteps", "sc_nsteps"),
    ):
        if k in a:
            res[f] = int(a[k])
    if "odeint_algorithm" in a:
        res.odeintAlgorithm = str(a.odeint_algorithm)
        res.odeintEpsabs = float(a.odeint_epsabs)
        res.odeintEpsrel = float(a.odeint_epsrel)
    if cls != e["class"]:
        res.fieldMapInterpolation = "cubic"

    def _field_map(model_field, text):
        res[model_field] = _write_field_map_lib_file(
            t, model_field, res.name, text, qcall, field_map_cache
        )

    def _field_map_1d(field, hz, scale):
        res.fieldSource = "fieldMap"
        res.l = (len(field) - 1) * float(hz)
        res.rescaleMode = "factor"
        res.scaleFactor = scale
        b = io.StringIO()
        numpy.savetxt(b, numpy.column_stack([numpy.arange(len(field)) * hz, field]))
        _field_map("fieldMapFile", b.getvalue())

    def _rf_scale():
        return float(numpy.sqrt(a.P_actual / a.P_map) * a.scaling_factor)

    # multiplies the field of an element this app has no scaling for
    sf = float(a.get("scaling_factor", 1.0))
    if cls == "Bpm":
        res.resolution = float(a.resolution)
    elif cls == "Coil":
        res.l = float(c.length)
        res.b_field = float(c.B0) * sf
        res.radius = float(c.R)
    elif cls == "Corrector":
        res.h_kick, res.v_kick = (float(x) * sf for x in numpy.ravel(a.strength))
    elif cls == "Quadrupole":
        res.strengthType = "gradient"
        res.gradient = float(a.gradient)
    elif cls == "Sextupole":
        res.strengthType = "gradient"
        res.gradient = float(a.gradient) * sf
    elif cls == "RF_FieldMap_1d":
        res.frequency = float(c.frequency)
        res.phase = float(a.phid)
        _field_map_1d(numpy.real(c.Ez), c.hz, _rf_scale())
    elif cls == "RF_FieldMap_2d":
        res.fieldSource = "2dFieldMap"
        res.frequency = float(c.frequency)
        res.phase = float(a.phid)
        res.l = (c.Ez.shape[0] - 1) * float(c.hz)
        b = io.StringIO()
        lume_rftrack.utils.write_field_map_2d(
            b,
            numpy.real(c.Er) * _rf_scale(),
            numpy.real(c.Ez) * _rf_scale(),
            c.hr,
            c.hz,
        )
        _field_map("fieldMapFile2d", b.getvalue())
    elif cls == "SBend":
        res.angle = float(a.angle)
        res.e1 = float(a.E1)
        res.e2 = float(a.E2)
        res.k1 = float(a.K1)
        res.hgap = float(a.hgap)
        # an archive written before fint was measured has none
        res.fint = float(a.get("fint", 0.0))
    elif cls == "Screen":
        # RF-Track's unlimited size is infinite, this app's 0
        for f in ("width", "height"):
            res[f] = float(a[f]) if numpy.isfinite(a[f]) else 0.0
    elif cls == "Solenoid":
        res.fieldSource = "analytic"
        res.l = float(c.length)
        res.b_field = float(c.B0)
        res.radius = float(c.R)
    elif cls == "Static_Magnetic_FieldMap_1d":
        _field_map_1d(numpy.asarray(c.Bz), c.hz, float(a.scaling_factor))
    return res


def _lume_rftrack_import_errors(archive):
    """Why `archive` (`read_archive()`'s) can't be imported, one message
    per problem, or none."""
    import lume_rftrack.archive

    res = []
    rigidity = []
    a = [x[0] for x in SCHEMA.enum.OdeintAlgorithm]
    for i, e in enumerate(archive.elements):
        n = f"element {i} {str(e.name)!r} ({e['class']})"
        cls = lume_rftrack.archive.constructor_class(e["class"])
        if cls not in _LUME_RFTRACK_CLASS_TO_TYPE:
            res.append(f"{n} has no element type in this app")
            continue
        c = e.get("constructor", PKDict())
        if str(e.attributes.get("odeint_algorithm", "rk2")) not in a:
            res.append(
                f"{n} has odeint_algorithm={e.attributes.odeint_algorithm}, which"
                + " isn't supported"
            )
        for k in ("static_Bfield", "static_Efield"):
            if numpy.any(e.attributes.get(k, 0.0)):
                res.append(f"{n} has a {k}, which this app doesn't support")
        if "z1" in e.attributes:
            f = c.Ez if "Ez" in c else c.Bz
            if not numpy.allclose(
                [e.attributes.z0, e.attributes.z1],
                [0.0, (numpy.shape(f)[0] - 1) * c.hz],
            ):
                res.append(
                    f"{n} uses only z0={e.attributes.z0} to z1={e.attributes.z1}"
                    + " of its field map"
                )
        if cls == "SBend":
            if archive.beamline_class == "Volume":
                res.append(f"{n} is a bend in a Volume; bends need a Lattice")
            rigidity.append(abs(float(e.attributes.P_over_Q)))
        elif cls in ("RF_FieldMap_1d", "RF_FieldMap_2d"):
            if c.direction != 1:
                res.append(f"{n} has direction={c.direction}; only 1 is supported")
            if any(numpy.any(numpy.imag(c[k])) for k in ("Er", "Ez") if k in c):
                res.append(f"{n} has a complex field map")
        if (
            cls == "RF_FieldMap_1d"
            and c.length != -1
            and not numpy.isclose(c.length, (len(c.Ez) - 1) * c.hz)
        ):
            res.append(f"{n} is {c.length} m long, not its field map's length")
    if rigidity and not numpy.allclose(rigidity, rigidity[0], rtol=1e-9):
        res.append(
            f"its bends have different rigidities P_over_Q={sorted(set(rigidity))}"
        )
    if archive.integrator and str(archive.integrator.odeint_algorithm) not in a:
        # e.g. msadams, which this RF-Track can't integrate with
        res.append(
            f"its odeint_algorithm={archive.integrator.odeint_algorithm} isn't supported"
        )
    return res


def _openpmd_job_cmd_file(run_dir, npy_filename):
    """Convert a saved phase-space file to an OpenPMD-BeamPhysics HDF5 file.

    `lume_rftrack.utils.PHASE_SPACE_COLUMNS` are already in the units
    ParticleGroup expects (x/y/z in m, Px/Py/Pz in eV/c, t in s, weight in
    C), so no unit
    conversion is needed here -- only a column selection and reshuffle.

    Raises:
        sirepo.util.UserAlert: the beam's particle isn't a species openPMD
            beamphysics knows
    """
    dm = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models
    if dm.beam.particle not in _particle_mass_and_charge():
        raise sirepo.util.UserAlert(
            f"openPMD export supports {', '.join(sorted(_particle_mass_and_charge()))}"
            f" beams, not particle={dm.beam.particle}"
        )
    ps = numpy.load(str(run_dir.join(npy_filename)))
    n = len(ps)
    c = lume_rftrack.utils.PHASE_SPACE_COLUMNS.index
    pg = beamphysics.ParticleGroup(
        data=PKDict(
            x=ps[:, c("x")],
            y=ps[:, c("y")],
            z=ps[:, c("z")],
            px=ps[:, c("Px")],
            py=ps[:, c("Py")],
            pz=ps[:, c("Pz")],
            t=ps[:, c("t")],
            weight=ps[:, c("weight")],
            species=dm.beam.particle,
            status=numpy.ones(n),
        )
    )
    fn = re.sub(r"\.npy$", "", npy_filename) + "_openpmd.h5"
    p = run_dir.join(fn)
    if p.exists():
        p.remove()
    pg.write(str(p))
    return template_common.JobCmdFile(reply_path=p, reply_uri=fn)


def _output_info(data, run_dir):
    res = []
    if run_dir.join(_STATS_FILE).exists():
        for model_key in ("statAnimation", "stat2Animation"):
            res.append(
                PKDict(
                    columns=stat_columns(),
                    name="Beam Variables",
                    modelKey=model_key,
                    report=model_key,
                    frameCount=1,
                )
            )
    if run_dir.join(_BPMS_FILE).exists():
        res.append(
            PKDict(
                name="Beam Position at Monitors",
                modelKey="bpmAnimation",
                report="bpmAnimation",
                frameCount=1,
            )
        )
    names = _screen_names(data)
    for idx, name in enumerate(names):
        fn = _SCREEN_FILE.format(idx)
        if run_dir.join(fn).exists():
            res.append(
                PKDict(
                    modelKey=f"elementAnimation{idx}",
                    reportIndex=idx,
                    report="elementAnimation",
                    name=name,
                    frameCount=1,
                    filename=fn,
                )
            )
    # Always show the final tracked beam as its own plot, regardless of
    # whether the beamline happens to end with a SCREEN element.
    if run_dir.join(_FINAL_PARTICLES_FILE).exists():
        idx = len(names)
        res.append(
            PKDict(
                modelKey=f"elementAnimation{idx}",
                reportIndex=idx,
                report="elementAnimation",
                name="Final Particles",
                frameCount=1,
                filename=_FINAL_PARTICLES_FILE,
            )
        )
    return res


def _particle_mass_and_charge():
    """`{particle: (mass [MeV/c^2], charge [e])}` for every named
    `beam.particle`, from the schema; "other" has neither.
    """
    return SCHEMA.constants.particleMassAndCharge


def _phase_space_plot(model, values):
    return template_common.heatmap(
        values=[
            values[:, lume_rftrack.utils.PHASE_SPACE_COLUMNS.index(model.x)],
            values[:, lume_rftrack.utils.PHASE_SPACE_COLUMNS.index(model.y)],
        ],
        model=model,
        plot_fields=PKDict(
            x_label=_axis_label(model.x),
            y_label=_axis_label(model.y),
            title="",
            # TODO(pjm): should be a different setting (show empty space as alpha=0)
            threshold=[1e-20, 1e20],
        ),
    )


def _read_data(run_dir):
    return simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))


def _rough_percent_complete(run_dir):
    """A rough running estimate from RF_Track's own verbosity progress
    output, not an exact one: `t` (mm/c) is `c * t_phys`, the distance
    light would travel in the elapsed time, and a particle moving at
    close to c covers very nearly that same physical distance -- true
    for all but a brief low-energy stretch near a cathode, negligible
    against a typical multi-meter tracking range -- so the last `t`
    printed so far, divided by the tracking range's own end position
    (both in mm), stands in for actual progress through it.

    The end position is the one the generated script actually tracks to:
    the Volume's tracking range (`_tracking_range()`), or the end of the
    last element for a Lattice, which has no tracking range.

    Returns:
        float: 0 whenever that's not yet knowable -- run.log doesn't
            exist yet, has no progress line in it yet, or this report
            doesn't track at all (e.g. a bunchReport)
    """
    log = run_dir.join(template_common.RUN_LOG)
    if not log.exists():
        return 0
    data = _read_data(run_dir)
    if "bunchReport" in data.get("report", ""):
        return 0
    data = _evaluated_data(data)
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    elements = _generate_lattice(util, util.select_beamline().id, [])
    if data.models.simulation.elementPosition == "relative":
        s1_mm = max((e.elemedge + e.l for e in elements), default=0) * 1e3
    else:
        s1_mm = _tracking_range(data.models.simulationSettings, elements)[1] * 1e3
    if s1_mm <= 0:
        return 0
    m = _VERBOSITY_T_RE.findall(pykern.pkio.read_text(log))
    if not m:
        return 0
    # not 100: is_running is still True, and the true final t can run a
    # little past this rough estimate's own denominator (see the
    # docstring's "brief low-energy stretch" caveat) -- 100 is reserved
    # for the one time this is actually known, once the job is done
    return min(99, float(m[-1]) * 100.0 / s1_mm)


def _screen_names(data):
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    beamline_id = int(
        data.models.simulation.visualizationBeamlineId or data.models.beamlines[0].id
    )
    res = []
    for item_id in util.explode_beamline(beamline_id):
        item = util.get_item(abs(item_id))
        if item.get("type") == "SCREEN":
            res.append(item.name)
    return res


def _sequential_elements(elements):
    """Convert absolute (possibly gapped) elemedge positions into a
    strictly sequential list, as required by rft.Lattice.append(), which
    has no notion of position -- each appended element simply begins where
    the previous one ended.

    A gap between two elements becomes a synthetic Drift; elements are
    otherwise unaware of this, so it doesn't affect the true beamline in
    Volume mode. Overlapping elements have no sequential representation at
    all (e.g. a gun cavity and a bucking solenoid occupying the same
    physical space) and are rejected here, rather than silently
    mis-tracked.
    """
    res = []
    prev_end = None
    prev_name = None
    for i, el in enumerate(elements):
        if prev_end is not None:
            gap = el.elemedge - prev_end
            if gap < -1e-9:
                raise sirepo.util.UserAlert(
                    f'"{el.name}" (starting at {el.elemedge} m) overlaps'
                    f' "{prev_name}" (ending at {prev_end} m) -- overlapping'
                    " elements require Absolute (Volume) positioning,"
                    " not Sequential (Lattice).",
                    "elements overlap in lattice mode",
                )
            if gap > 1e-9:
                res.append(
                    _SIM_DATA.model_defaults("DRIFT").pkupdate(
                        type="DRIFT",
                        name=f"_gap{i}",
                        l=gap,
                        elemedge=prev_end,
                        apertureShape=el.apertureShape,
                        aperture_x=el.aperture_x,
                        aperture_y=el.aperture_y,
                    )
                )
        res.append(el)
        prev_end = el.elemedge + el.l
        prev_name = el.name
    return res


def _space_charge_spec(simulation_settings):
    """`simulationSettings` as lume_rftrack space-charge settings (see
    `_PIC_SPACE_CHARGE_FIELDS`), empty for no space charge.
    """
    if simulation_settings.spaceCharge == "none":
        return PKDict()
    res = PKDict(kind=simulation_settings.spaceCharge)
    if res.kind == "pic":
        for k, f in _PIC_SPACE_CHARGE_FIELDS.items():
            res[k] = (
                tuple(simulation_settings[x] for x in f)
                if isinstance(f, tuple)
                else simulation_settings[f]
            )
    return res


def _stat_animation_plot(frame_args):
    v = numpy.load(str(frame_args.run_dir.join(_STATS_FILE)))
    plots = []
    for f in ("y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] == _NONE:
            continue
        plots.append(
            PKDict(
                label=_STAT_LABELS[frame_args[f]],
                dim=f,
                points=v[
                    :, lume_rftrack.utils.STAT_COLUMNS.index(frame_args[f])
                ].tolist(),
            )
        )
    x_name = frame_args.x if frame_args.x != _NONE else "s"
    return template_common.parameter_plot(
        x=v[:, lume_rftrack.utils.STAT_COLUMNS.index(x_name)].tolist(),
        plots=plots,
        model=frame_args,
        plot_fields=PKDict(
            dynamicYLabel=True,
            title="",
            y_label="",
            x_label=_STAT_LABELS[x_name],
        ),
    )


def _tracking_range(simulation_settings, elements):
    """`(s0, s1)` [m]: the range the generated script passes to
    Volume.set_s0()/set_s1().

    Those gate which portion of every element's field is active during
    tracking (not merely where particles are reported), so with
    `autoTrackingRange` an element positioned to start before the beam
    origin -- e.g. a solenoid whose field map's own s=0 reference sits
    upstream of the cathode -- widens the range to its full extent;
    otherwise that leading portion would be silently excluded from the
    field the beam feels.
    """
    if simulation_settings.autoTrackingRange == "1":
        return (
            min((e.elemedge for e in elements), default=0.0),
            max((e.elemedge + e.l for e in elements), default=1.0),
        )
    return simulation_settings.trackingS0, simulation_settings.trackingS1


def _unique_name(prefix, names):
    """`prefix` and the first index from 1 that isn't in `names`, as the
    lattice editor's uniqueNameForType() names a new element"""
    i = 1
    while f"{prefix}{i}" in names:
        i += 1
    return f"{prefix}{i}"


def _write_distribution_lib_file(particle_group, name, qcall):
    """Write the archive's `particle_group` as a brand new lib file for
    `beam.distributionFile`. Reuses the same
    write-a-new-lib-file-during-import mechanism as
    `_write_field_map_lib_file`, just for the beam model instead of a
    CAVITY/SOLENOID element.

    Only callable with a real `qcall` -- see
    `sirepo.sim_data.rftrack.SimData.prepare_import_file_args`'s own
    docstring for why this has to happen on the server, not in
    `stateful_compute_import_file` (the job agent).

    Returns:
        str: the plain basename to store in `beam.distributionFile`

    Raises:
        sirepo.util.UserAlert: a lib file of the same name already
            exists with *different* content -- same reason
            `_write_field_map_lib_file` guards against this: the lib
            directory is shared across every simulation this user has
            of this sim type, so re-importing the very same archive (a
            normal thing to do while iterating) would otherwise
            collide with itself on every single retry.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".h5") as t:
        particle_group.write(t.name)
        t.flush()
        # a portion of the file's own md5 in the basename, same
        # convention as track_parser.validate_file()'s _hashed_name()
        # -- this lib file is shared across every simulation this user
        # has of this sim type (not per-simulation), so without this,
        # re-importing a different archive that happens to reuse the
        # same `name` (e.g. two sims both imported from a file called
        # "archive.h5") would silently overwrite an unrelated sim's
        # distribution file.
        basename = f"{name}-{pykern.pkio.py_path(t.name).computehash()[:8]}.h5"
        with open(t.name, "rb") as bf:
            content = bf.read()
    _write_lib_file_once(
        _SIM_DATA.lib_file_name_with_model_field("beam", "distributionFile", basename),
        content,
        f"distribution file='{basename}' already exists with different content;"
        + " rename and import again",
        qcall,
    )
    return basename


def _write_field_map_lib_file(
    el_type, model_field, element_name, text, qcall, field_map_cache
):
    """Write `text`, a field map in the format `lume_rftrack.utils`
    reads (`load_field_map()`'s two columns, or
    `load_field_map_2d()`'s), as a lib file for `el_type`'s
    `model_field`, named after the archived element plus a portion of its
    md5, so it's recognizable in the lattice editor and can't collide
    with another archive's map of the same element name.

    `field_map_cache` ({(el_type, model_field, md5): basename}) is shared
    across every element in one import (see `build_imported_data()`):
    several elements built from the same field-map file (e.g. a linac's
    identical accelerating cavities) are archived with one shared copy
    (`lume_rftrack.archive._dedupe_field_maps()`), and reusing the one
    lib file written for that content keeps that true on import too.

    Only callable with a real `qcall`: see
    `sirepo.sim_data.rftrack.SimData.prepare_import_file_args`.

    Returns:
        str: the plain basename to store in `model_field`
    """
    import hashlib

    h = hashlib.md5(text.encode()).hexdigest()
    k = (el_type, model_field, h)
    if k in field_map_cache:
        return field_map_cache[k]
    basename = f"{element_name}-{h[:8]}.dat"
    _write_lib_file_once(
        _SIM_DATA.lib_file_name_with_model_field(el_type, model_field, basename),
        text,
        f"field map file='{basename}' already exists with different content;"
        + f" rename element '{element_name}' and import again",
        qcall,
    )
    field_map_cache[k] = basename
    return basename


def _write_lib_file_once(full_name, content, alert, qcall):
    """Write `content` (str or bytes) to lib file `full_name`, unless the
    file already holds exactly that.

    The lib directory is shared by every simulation of this type, so
    re-importing the same archive finds its own earlier file, which is
    fine; a same-named file with different content is not.

    Raises:
        sirepo.util.UserAlert: `alert`, when `full_name` exists with
            different content
    """
    if _SIM_DATA.lib_file_exists(full_name, qcall=qcall):
        r = (
            _SIM_DATA.lib_file_read_binary
            if isinstance(content, bytes)
            else _SIM_DATA.lib_file_read_text
        )
        if r(full_name, qcall=qcall) == content:
            return
        raise sirepo.util.UserAlert(alert)
    _SIM_DATA.lib_file_write(full_name, content, qcall=qcall)
