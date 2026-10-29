"""OPAL execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import hdf5_util
from sirepo.template import lattice
from sirepo.template import sdds_util
from sirepo.template import template_common
from sirepo.template import track_parser
from sirepo.template.lattice import LatticeUtil
import math
import numpy
import re
import scipy.constants
import sirepo.lib
import sirepo.sim_data
import sirepo.template.madx_converter

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

OPAL_INPUT_FILE = "opal.in"
OPAL_OUTPUT_FILE = "opal.out"
OPAL_POSITION_FILE = "opal-vtk.py"

_DIM_INDEX = PKDict(
    x=0,
    y=1,
    z=2,
)
_OPAL_PI = 3.14159265358979323846
_OPAL_CONSTANTS = PKDict(
    pi=_OPAL_PI,
    twopi=_OPAL_PI * 2.0,
    # note: OPAL's raddeg and raddeg have the opposite behavior of MAD-X
    raddeg=180.0 / _OPAL_PI,
    degrad=_OPAL_PI / 180.0,
    e=2.7182818284590452354,
    emass=0.51099892e-03,
    pmass=0.93827204e00,
    hmmass=0.939277e00,
    umass=238 * 0.931494027e00,
    cmass=12 * 0.931494027e00,
    mmass=0.10565837,
    dmass=2 * 0.931494027e00,
    xemass=124 * 0.931494027e00,
    clight=299792458.0,
    p0=1,
    seed=123456789,
)
OPAL_H5_FILE = "opal.h5"
# a beamline's absolute position, see opal.js BEAMLINE_POSITION_FIELDS
_BEAMLINE_POSITION_FIELDS = ("phi", "psi", "theta", "x", "y", "z")
_OPAL_SDDS_FILE = "opal.stat"
_OPAL_VTK_FILE = "opal_ElementPositions.vtk"
_ELEMENTS_WITH_TYPE_FIELD = ("CYCLOTRON", "MONITOR", "RFCAVITY")
_HEADER_COMMANDS = ("option", "filter", "geometry", "particlematterinteraction", "wake")


class LibAdapter(sirepo.lib.LibAdapterBase):
    def parse_file(self, path):
        from sirepo.template import opal_parser

        data, input_files = opal_parser.parse_file(
            pkio.read_text(path),
            filename=path.basename,
            update_filenames=False,
        )
        self._verify_files(path, [f.filename for f in input_files])
        return self._convert(data)

    def write_files(self, data, source_path, dest_dir):
        """writes files for the simulation

        Returns:
            PKDict: structure of files written (debugging only)
        """

        class _G(_Generate):
            def _input_file(self, model_name, field, filename):
                return f'"{filename}"'

            def _output_file(self, model, field):
                return f'"{model[field]}"'

        g = _G(data)
        r = PKDict(commands=dest_dir.join(source_path.basename))
        pkio.write_text(r.commands, g.sim())
        self._write_input_files(data, source_path, dest_dir)
        r.output_files = (
            LatticeUtil(data, SCHEMA)
            .iterate_models(
                OpalOutputFileIterator(preserve_output_filenames=True),
            )
            .result.keys_in_order
        )
        return r


class OpalElementIterator(lattice.ElementIterator):
    def __init__(self, formatter, visited=None):
        super().__init__(None, formatter)
        self.visited = visited

    def end(self, model):
        if self.visited:
            if "_id" in model and model._id not in self.visited:
                return
        super().end(model)

    def is_ignore_field(self, field):
        return field == "name" or field == self.IS_DISABLED_FIELD


class _OpalLogParser(template_common.LogParser):
    def _parse_log_line(self, line):
        if re.search(r"^Error.*?>\s*[\w\"]", line):
            l = re.sub(r"Error.*?>\s*", "", line.rstrip()).rstrip()
            if re.search(r"1DPROFILE1-DEFAULT", l):
                return None
            if l:
                return l + "\n"
        return None


class OpalOutputFileIterator(lattice.ModelIterator):
    def __init__(self, preserve_output_filenames=False):
        self.result = PKDict(
            keys_in_order=[],
        )
        self.model_index = PKDict()
        self.preserve_output_filenames = preserve_output_filenames

    def field(self, model, field_schema, field):
        if field == lattice.ElementIterator.IS_DISABLED_FIELD or field == "_super":
            return
        self.field_index += 1
        # for now only interested in element outfn output files
        if field == "outfn" and field_schema[1] == "OutputFile":
            if self.preserve_output_filenames:
                filename = model[field]
            else:
                filename = "{}.{}.h5".format(model.name, field)
            k = LatticeUtil.file_id(model._id, self.field_index)
            self.result[k] = filename
            self.result.keys_in_order.append(k)

    def start(self, model):
        self.field_index = 0
        self.model_name = LatticeUtil.model_name_for_data(model)
        if self.model_name in self.model_index:
            self.model_index[self.model_name] += 1
        else:
            self.model_index[self.model_name] = 1


class OpalMadxConverter(sirepo.template.madx_converter.MadxConverter):
    # MadxConverter's settings, see MadxConverter
    _CONSTANTS = _OPAL_CONSTANTS
    _DIPEDGE_BENDS = ("SBEND", "RBEND")
    _ELEMENT_POSITION = "relative"
    _THICKEN_THIN_CAVITIES = True
    # OPAL has no fringe field integral
    _DIPEDGE_FIELDS = PKDict(entrance=PKDict(e1="e1"), exit=PKDict(e1="e2"))
    _DIPEDGE_GAP = ("gap", 2)
    # OPAL's other particles are given by MASS and CHARGE
    _PARTICLE_MAP = PKDict(
        antiproton="ANTIPROTON",
        electron="ELECTRON",
        negmuon="MUON",
        positron="POSITRON",
        proton="PROTON",
    )
    _ELEMENTS = PKDict(
        DRIFT=["DRIFT", "l"],
        ECOLLIMATOR=["ECOLLIMATOR", "l", "xsize", "ysize"],
        HKICKER=["HKICKER", "l", "kick", "psi=tilt"],
        KICKER=["KICKER", "l", "hkick", "vkick", "psi=tilt"],
        MARKER=["MARKER"],
        MONITOR=["HMONITOR", "l"],
        # OPAL's MULTIPOLE is thick, see _to_madx_multipole()
        MULTIPOLE=["MULTIPOLE", "psi=tilt"],
        OCTUPOLE=["OCTUPOLE", "l", "k3", "k3s", "psi=tilt"],
        QUADRUPOLE=["QUADRUPOLE", "l", "k1", "k1s", "psi=tilt"],
        RBEND=["RBEND", "l", "angle", "e1", "psi=tilt"],
        RCOLLIMATOR=["RCOLLIMATOR", "l", "xsize", "ysize"],
        RFCAVITY=["RFCAVITY", "l", "volt", "freq"],
        SBEND=["SBEND", "l", "angle", "e1", "e2", "psi=tilt"],
        SEXTUPOLE=["SEXTUPOLE", "l", "k2", "k2s", "psi=tilt"],
        # TODO(pjm): compute dks from ksi?
        SOLENOID=["SOLENOID", "l", "ks"],
        TRAVELINGWAVE=["TWCAVITY", "l", "volt", "freq", "dlag=delta_lag"],
        VKICKER=["VKICKER", "l", "kick", "psi=tilt"],
    )
    _FROM_MADX = PKDict(
        # type and size from apertype and aperture, see _from_madx_collimator()
        COLLIMATOR="ECOLLIMATOR",
        # merged into the bend beside it, see _merge_dipedges()
        DIPEDGE=None,
        DRIFT="DRIFT",
        ECOLLIMATOR="ECOLLIMATOR",
        HKICKER="HKICKER",
        HMONITOR="MONITOR",
        INSTRUMENT="DRIFT",
        KICKER="KICKER",
        MARKER="MARKER",
        MONITOR="MONITOR",
        MULTIPOLE="MULTIPOLE",
        OCTUPOLE="OCTUPOLE",
        PLACEHOLDER="DRIFT",
        QUADRUPOLE="QUADRUPOLE",
        RBEND="RBEND",
        RCOLLIMATOR="RCOLLIMATOR",
        RFCAVITY="RFCAVITY",
        SBEND="SBEND",
        SEXTUPOLE="SEXTUPOLE",
        SOLENOID="SOLENOID",
        TWCAVITY="TRAVELINGWAVE",
        VKICKER="VKICKER",
        VMONITOR="MONITOR",
    )

    #: The fringe field of OPAL's default bend profile (1DPROFILE1-DEFAULT),
    #: measured by tracking against MAD-X PTC, is about MAD-X's with
    #: hgap = GAP / 2 and this fint. lib/SBEND-fmapfn.hard_edge_profile.txt
    #: isn't used for a hard edge: it has no vertical edge focusing.
    _DEFAULT_PROFILE_FINT = 0.37

    #: field strengths [T/m^n] which are MAD-X's [1/m^(n+1)] times brho
    _MULTIPOLE_ORDER = PKDict(QUADRUPOLE=1, SEXTUPOLE=2, OCTUPOLE=3)

    #: Fourier components per point of a RFCAVITY field map, and its points
    #: per RF wavelength, enough for OPAL's reconstructed map to match
    _RF_FIELD_MAP_ACCURACY = 0.4
    _RF_FIELD_MAP_POINTS = 600

    def __init__(self, qcall, **kwargs):
        super().__init__(SIM_TYPE, qcall=qcall, **kwargs)

    def _beam_to_madx(self, data, madx):
        """OPAL's energy and particle as written, then its beam"""
        mb = LatticeUtil.find_first_command(madx, "beam")
        ob = LatticeUtil.find_first_command(data, "beam")
        for f in ob:
            # OPAL's npart is the macro-particle count, MAD-X's the bunch's;
            # OPAL's mass and charge default to 0, the particle's in MAD-X
            if (
                f in mb
                and f in SCHEMA.model.command_beam
                and f
                not in (
                    "charge",
                    "mass",
                    "npart",
                )
            ):
                mb[f] = ob[f]
                if f in ("gamma", "energy", "pc") and mb[f]:
                    madx.models.bunch.beamDefinition = f
        mb.particle = self._particle_to_madx(ob.particle)
        if mb.particle == "other":
            mb.particle = self._madx_particle(self.beam.mass, self.beam.charge)
        if mb.particle == "other":
            # ex. CARBON, or MASS and CHARGE
            mb.mass = self.beam.mass
            mb.charge = self.beam.charge
        return self._beam_for_madx(
            npart=(
                # bunch charge [C] to particles
                self._val(ob.bcurrent)
                / (self._val(ob.bfreq) * 1e6)
                / scipy.constants.e
                / abs(self.beam.charge)
                if self._val(ob.bcurrent) and self._val(ob.bfreq)
                else None
            ),
            particle_count=self._val(ob.npart) or None,
            **self.__madx_distribution(data),
        )

    def _element_handlers(self):
        return PKDict(
            from_madx=PKDict(
                COLLIMATOR=self._from_madx_collimator,
                MULTIPOLE=self._from_madx_multipole,
                OCTUPOLE=self._from_madx_quadrupole,
                QUADRUPOLE=self._from_madx_quadrupole,
                RBEND=self._from_madx_rbend,
                RFCAVITY=self._from_madx_rfcavity,
                SBEND=self._from_madx_sbend,
                SEXTUPOLE=self._from_madx_quadrupole,
                SOLENOID=self._from_madx_solenoid,
                TWCAVITY=self._from_madx_twcavity,
            ),
            to_madx=PKDict(
                MULTIPOLE=self._to_madx_multipole,
                OCTUPOLE=self._to_madx_quadrupole,
                QUADRUPOLE=self._to_madx_quadrupole,
                RBEND=self._to_madx_rbend,
                RFCAVITY=self._to_madx_rfcavity,
                SBEND=self._to_madx_sbend,
                SEXTUPOLE=self._to_madx_quadrupole,
                SOLENOID=self._to_madx_solenoid,
                TRAVELINGWAVE=self._to_madx_travelingwave,
            ),
        )

    def _fixup_element(self, element_in, element_out):
        super()._fixup_element(element_in, element_out)
        if self.from_class.sim_type() == SIM_TYPE:
            self.__aperture_to_madx(element_in, element_out)
        elif element_in.type not in ("COLLIMATOR", "RBEND", "SBEND"):
            # OPAL refuses APERTURE on a bend, see __bend_gap()
            self.__aperture_from_madx(element_in, element_out)

    def _fixup_from_madx(self, madx, data, beam):
        mb = LatticeUtil.find_first_command(madx, "beam")
        LatticeUtil.find_first_command(data, "option").version = 20000
        b = LatticeUtil.find_first_command(data, "beam")
        b.particle = self._particle_from_madx(mb.particle) or ""
        if not b.particle:
            b.mass = self.beam.mass
            b.charge = self.beam.charge
        LatticeUtil.find_first_command(data, "beam").pc = self.particle_energy.pc
        t = LatticeUtil.find_first_command(data, "track")
        t.line = data.models.simulation.visualizationBeamlineId
        # track to the end of the beamline, as opal.js updateZStop(): the
        # design path, so MAD-X's arc lengths (ids are the same)
        u = LatticeUtil(madx, self.from_class.schema())
        t.zstop = round(
            sum(
                self._val(u.get_item(abs(i)).get("l", 0))
                for i in u.explode_beamline(t.line)
            ),
            6,
        )
        self.__fixup_distribution(madx, data, beam)
        for b, c in self.__rf_field_maps.items():
            _SIM_DATA.lib_file_write(
                _SIM_DATA.lib_file_name_with_model_field("RFCAVITY", "fmapfn", b),
                c,
                qcall=self.qcall,
            )
        _default_lattice_overlay(data)

    def _fixup_to_madx(self, data, madx):
        # OPAL's built-in constants the beam or lattice use
        self.__madx_constants(madx)

    def _from_madx_collimator(self, element_in, element_out):
        a = self._aperture(element_in)
        if a:
            element_out.xsize = a.x
            element_out.ysize = a.y
            if a.apertype == "rectangle":
                element_out.type = "RCOLLIMATOR"
        if not self._val(element_in.l):
            pkdlog(
                "COLLIMATOR={} has zero length, which OPAL-T doesn't apply",
                element_in.name,
            )

    def _from_madx_multipole(self, element_in, element_out):
        pkdlog(
            "thin MULTIPOLE={} has no OPAL equivalent, replaced by a MARKER",
            element_in.name,
        )
        element_out.type = "MARKER"

    def _from_madx_quadrupole(self, element_in, element_out):
        for f in self.__multipole_fields(element_in.type):
            element_out[f] = self.__to_brho(element_out[f])

    def _from_madx_rbend(self, element_in, element_out):
        self.__bend_design(element_in, element_out)

    def _from_madx_rfcavity(self, element_in, element_out):
        # OPAL's lag [rad] is relative to the autophased crest
        element_out.lag = 2 * math.pi * self._crest_offset(element_in.lag)
        m = self.__rf_field_map(element_in)
        if m:
            element_out.fmapfn = m.basename
            element_out.rfcavity_type = "STANDING"
            # MV to the field map's peak [MV/m]
            element_out.volt = self._val(element_in.volt) / m.gain
            self.__rf_field_maps[m.basename] = m.content
        else:
            pkdlog(
                "RFCAVITY={} without length or frequency has no OPAL field map, replaced by a DRIFT",
                element_in.name,
            )
            element_out.type = "DRIFT"

    def _from_madx_sbend(self, element_in, element_out):
        angle = self._val(element_in.angle)
        if angle != 0:
            # MAD-X's arc length to OPAL's chord length
            length = self._val(element_in.l)
            d1 = 2 * length / angle
            element_out.l = d1 * math.sin(length / d1)
        self.__bend_design(element_in, element_out)

    def _from_madx_solenoid(self, element_in, element_out):
        element_out.ks = self.__to_brho(element_out.ks)

    def _from_madx_twcavity(self, element_in, element_out):
        # OPAL's lag [rad] is relative to the autophased crest
        element_out.lag = 2 * math.pi * self._crest_offset(element_in.lag)
        # MV to MV/m
        l = self._val(element_in.l)
        if l:
            element_out.volt = self._val(element_in.volt) / l

    def _init_from_madx(self, madx):
        # the RF cavities' field maps: written by _from_madx_rfcavity(),
        # saved by _fixup_from_madx()
        self.__rf_field_maps = PKDict()

    def _init_to_madx(self, data):
        """OPAL's absolute positions as relative ones, with drifts between
        elements, and its beam's energy"""

        def _get_element_by_id(data, id):
            for e in data.models.elements:
                if e._id == id:
                    return e
            raise AssertionError(
                f"id={id} not found in elements={data.models.elements}"
            )

        def _get_drift(distance):
            for e in data.models.elements:
                if e.l == distance and e.type == "DRIFT":
                    return e
            return False

        def _insert_drift(distance, beam_idx, items_idx, pos, length):
            d = _get_drift(distance)
            n = LatticeUtil.max_id(data) + 1
            m = "D" + str(n)
            if d:
                n = d._id
                m = d.name
            new_drift = PKDict(
                _id=n,
                l=distance,
                name=m,
                type="DRIFT",
            )
            if not d:
                data.models.elements.append(new_drift)
            data.models.beamlines[beam_idx]["items"].insert(
                items_idx + 1, new_drift._id
            )
            data.models.beamlines[beam_idx]["positions"].insert(
                items_idx + 1, PKDict(elemedge=str(float(pos) + length[0]))
            )

        def _flatten_beamlines():
            """An absolute beamline with beamlines in it, ex. sub-lines at
            elemedge=0, as its elements at their absolute positions, sorted"""
            cv = code_var(data.models.rpnVariables)
            bls = PKDict({b.id: b for b in data.models.beamlines})

            def _elements(beamline, offset):
                res = []
                for i, item in enumerate(beamline["items"]):
                    p = offset + cv.eval_var_with_assert(beamline.positions[i].elemedge)
                    if abs(item) in bls:
                        res.extend(_elements(bls[abs(item)], p))
                    else:
                        res.append((p, item))
                return res

            for b in data.models.beamlines:
                if not any(abs(i) in bls for i in b["items"]):
                    continue
                e = sorted(_elements(b, 0), key=lambda x: x[0])
                b["items"] = [i for _, i in e]
                b.positions = [PKDict(elemedge=str(p)) for p, _ in e]

        def _get_distance_and_insert_drift(beamline, beam_idx):
            cv = code_var(data.models.rpnVariables)
            if beamline["items"]:
                # the space before the first element, which starts the line
                d = round(cv.eval_var_with_assert(beamline.positions[0].elemedge), 10)
                if d > 0:
                    _insert_drift(d, beam_idx, -1, -d, [d])
            for i, e in enumerate(beamline["items"]):
                if i + 1 == len(beamline["items"]):
                    break
                if _get_element_by_id(data, e).type == "DRIFT":
                    continue
                # positions may be expressions, ex. "DQ2_POS-YAG4_POS"
                p = cv.eval_var_with_assert(beamline.positions[i].elemedge)
                n = cv.eval_var_with_assert(beamline.positions[i + 1].elemedge)
                el = _get_element_by_id(data, e)
                l = cv.eval_var(el.l)
                if el.type == "SBEND":
                    # elemedge is along the design path: the arc, not l (chord)
                    a = cv.eval_var_with_assert(el.angle)
                    if a:
                        l = [l[0] * a / (2 * math.sin(a / 2))]
                d = round(n - p - l[0], 10)
                if d > 0:
                    _insert_drift(d, beam_idx, i, p, l)
                elif d < 0:
                    pkdlog(
                        "beamline={} element={} overlaps the next by {} m, MAD-X places them in sequence",
                        beamline.name,
                        el.name,
                        -d,
                    )

        if data.models.simulation.elementPosition == "absolute":
            _flatten_beamlines()
            for j, b in enumerate(data.models.beamlines):
                _get_distance_and_insert_drift(b, j)
        self.__normalize_opal_beam(data)

    def _to_madx_multipole(self, element_in, element_out):
        # thick [T/m^n] to a thin kick between half length drifts
        l = self._val(element_in.l)
        for f in ("kn", "ks"):
            v = [
                x * l / self.particle_energy.brho * (-1 if self.beam.charge < 0 else 1)
                for x in self._array_values(element_in[f])
            ]
            element_out[f + "l"] = self._array_text(v)
        if l:
            element_out.lrad = l
            d = PKDict(name=f"{element_in.name}_D", type="DRIFT", l=l / 2)
            self._add_inserts(element_out._id, before=[d], after=[d])

    def _to_madx_quadrupole(self, element_in, element_out):
        for f in self.__multipole_fields(element_in.type):
            element_out[f] = self.__from_brho(element_in[f])

    def _to_madx_rbend(self, element_in, element_out):
        element_out.hgap = self._val(element_in.gap) / 2

    def _to_madx_rfcavity(self, element_in, element_out):
        element_out.lag = self._lag_from_crest_offset(
            self._val(element_in.lag) / (2 * math.pi)
        )
        m = self.__rf_field_map(element_in)
        if m and element_in.fmapfn == m.basename:
            # the field map's peak [MV/m] to MV
            element_out.volt = round(self._val(element_in.volt) * m.gain, 12)

    def _to_madx_sbend(self, element_in, element_out):
        angle = self._val(element_in.angle)
        if angle != 0:
            # OPAL's chord length to MAD-X's arc length
            element_out.l = self._val(element_in.l) * angle / (2 * math.sin(angle / 2))
        element_out.hgap = self._val(element_in.gap) / 2

    def _to_madx_solenoid(self, element_in, element_out):
        element_out.ks = self.__from_brho(element_in.ks)

    def _to_madx_travelingwave(self, element_in, element_out):
        element_out.lag = self._lag_from_crest_offset(
            self._val(element_in.lag) / (2 * math.pi)
        )
        # MV/m to MV
        element_out.volt = self._val(element_in.volt) * self._val(element_in.l)

    def __aperture_from_madx(self, element_in, element_out):
        # MAD-X's half widths to OPAL's full widths
        a = self._aperture(element_in)
        if not a:
            return
        if a.apertype == "circle":
            element_out.aperture = f"circle({2 * a.x})"
        elif a.apertype in ("ellipse", "rectangle"):
            element_out.aperture = f"{a.apertype}({2 * a.x}, {2 * a.y})"
        else:
            pkdlog(
                "apertype={} has no OPAL equivalent, element={}",
                a.apertype,
                element_in.name,
            )

    def __aperture_to_madx(self, element_in, element_out):
        # OPAL's full widths to MAD-X's half widths
        m = re.search(r"^\s*(\w+)\s*\(([^)]*)\)", str(element_in.get("aperture") or ""))
        if (
            not m
            or "_APERTURE_ELEMENT"
            not in self.to_class.schema().model[element_out.type].get("_super", [])
            or element_in.aperture == SCHEMA.model._ELEMENT.aperture[2]
        ):
            return
        t = m.group(1).lower()
        a = [self._val(v) / 2 for v in m.group(2).split(",")]
        if t == "square":
            t = "rectangle"
            a = [a[0], a[0]]
        elif t not in ("circle", "ellipse", "rectangle"):
            pkdlog("aperture={} has no MAD-X equivalent", element_in.aperture)
            return
        element_out.apertype = t
        element_out.aperture = self._array_text(a[:1] if t == "circle" else a[:2])

    def __bend_design(self, element_in, element_out):
        """A MAD-X bend's design energy and GAP"""
        # kinetic energy in MeV
        element_out.designenergy = round(
            (self.particle_energy.energy - self.beam.mass) * 1e3,
            6,
        )
        element_out.gap = self.__bend_gap(element_in)

    def __bend_gap(self, element_in):
        """OPAL's GAP for a MAD-X bend: both the full vertical aperture
        (particles beyond GAP / 2 are lost) and the fringe field's extent,
        about MAD-X's with hgap = GAP / 2. Unset (0) is OPAL's default of
        2 cm, close to MAD-X's hard edge (hgap = 0).
        """
        h = self._val(element_in.hgap)
        if h:
            f = self._val(element_in.fint)
            if abs(f - self._DEFAULT_PROFILE_FINT) > 0.1:
                pkdlog(
                    "bend={} fint={} differs from OPAL's default profile, about fint={}",
                    element_in.name,
                    f,
                    self._DEFAULT_PROFILE_FINT,
                )
            return 2 * h
        a = self._aperture(element_in)
        if a:
            # vertical half aperture
            return 2 * a.y
        pkdlog(
            "bend={} has no hgap or aperture: OPAL's default GAP of 2 cm limits |y| to 1 cm",
            element_in.name,
        )
        return 0

    def __dispersion(self, beam, dist, beta_gamma):
        """The beam's horizontal dispersion as OPAL's x/pz and x'/pz
        correlations (R61, R62), with the total sigmas and x/x' correlation
        they imply; OPAL has no vertical ones"""
        d = PKDict({k: self._val(v) for k, v in beam.dispersion.items()})
        if d.get("dy") or d.get("dpy"):
            pkdlog(
                "OPAL beam has no vertical dispersion, dropped dy={} dpy={}",
                d.get("dy", 0),
                d.get("dpy", 0),
            )
        if not (d.get("dx") or d.get("dpx")):
            return
        if not ("beta_x" in beam.twiss and beam.ex is not None):
            pkdlog("OPAL beam without twiss, dropped dispersion={}", d)
            return
        b = self.particle_energy.beta
        # MAD-X's dispersion (with respect to PT) to eta (with respect to
        # delta = dp / p), and sigma E / E to sigma delta
        v = PKDict(
            eta=d.get("dx", 0) * b,
            etap=d.get("dpx", 0) * b,
            sd=self._val(beam.sige) / b**2,
            e=self._val(beam.ex),
            a=self._val(beam.twiss.alpha_x),
            bx=self._val(beam.twiss.beta_x),
        )
        v.sx = math.sqrt(v.e * v.bx + (v.eta * v.sd) ** 2)
        v.sxp = math.sqrt(v.e * (1 + v.a**2) / v.bx + (v.etap * v.sd) ** 2)
        dist.sigmax = v.sx
        dist.sigmapx = v.sxp * beta_gamma
        dist.corrx = (-v.e * v.a + v.eta * v.etap * v.sd**2) / (v.sx * v.sxp)
        dist.r61 = v.eta * v.sd / v.sx
        dist.r62 = v.etap * v.sd / v.sxp

    def __fixup_distribution(self, madx, data, beam):
        mb = LatticeUtil.find_first_command(madx, "beam")
        dist = LatticeUtil.find_first_command(data, "distribution")
        beta_gamma = self.particle_energy.beta * self.particle_energy.gamma
        self._replace_var(data, "brho", self.particle_energy.brho)
        self._replace_var(data, "gamma", self.particle_energy.gamma)
        self._replace_var(
            data,
            "beta",
            "sqrt(1 - (1 / ({} * {})))".format(
                self._var_name("gamma"),
                self._var_name("gamma"),
            ),
        )
        t = beam.twiss
        for dim in ("x", "y"):
            if beam[f"e{dim}"] is None:
                continue
            # ex, ey from exn, eyn, see MadxConverter.__normalize_madx_beam
            self._replace_var(data, f"emit_{dim}", beam[f"e{dim}"])
            if f"beta_{dim}" in t:
                dist[f"sigma{dim}"] = "sqrt({} * {})".format(
                    self._var_name(f"emit_{dim}"), self._var_name(f"beta_{dim}")
                )
                dist[f"sigmap{dim}"] = "sqrt({} * {}) * {} * {}".format(
                    self._var_name(f"emit_{dim}"),
                    self._var_name(f"gamma_{dim}"),
                    self._var_name("beta"),
                    self._var_name("gamma"),
                )
                dist[f"corr{dim}"] = "-{}/sqrt(1 + {} * {})".format(
                    self._var_name(f"alpha_{dim}"),
                    self._var_name(f"alpha_{dim}"),
                    self._var_name(f"alpha_{dim}"),
                )
        self.__dispersion(beam, dist, beta_gamma)
        # OPAL's default 3 sigma cut lowers the rms emittances by 5%; at 5
        # sigma, the rms values are MAD-X's (an uncut gaussian)
        for f in (
            "cutofflong",
            "cutoffpx",
            "cutoffpy",
            "cutoffpz",
            "cutoffx",
            "cutoffy",
        ):
            dist[f] = 5
        if beam.dp_s_coupling is not None:
            dist.corrz = self._var_name("dp_s_coupling")
        ob = LatticeUtil.find_first_command(data, "beam")
        if beam.npart:
            # the bunch's particles to the current at OPAL's bfreq [MHz]
            ob.bcurrent = (
                beam.npart
                * scipy.constants.e
                * abs(self.beam.charge)
                * self._val(ob.bfreq)
                * 1e6
            )
        else:
            ob.bcurrent = mb.bcurrent
        if beam.particle_count is not None:
            ob.npart = self._var_name("n_particles_per_bunch")
        if beam.sigt is not None:
            # c * sigma t to the bunch length in z
            dist.sigmaz = "{} * {}".format(self._val(beam.sigt), self._var_name("beta"))
        # sigma E / E to sigma (beta * gamma) = gamma * sigma E / E / beta
        dist.sigmapz = "{} * {} / {}".format(
            beam.sige, self._var_name("gamma"), self._var_name("beta")
        )

    def __from_brho(self, value):
        # OPAL field [T/m^n] to MAD-X normalized strength [1/m^(n+1)]
        m = re.search(
            r"^(.+?)\s*\*\s*{}$".format(re.escape(self._var_name("brho"))),
            str(value),
        )
        if m:
            # strength written by __to_brho()
            res = self._val(m.group(1))
        else:
            res = self._val(value) / self.particle_energy.brho
        if not res:
            return 0
        return -res if self.beam.charge < 0 else res

    def __madx_constants(self, madx):
        """OPAL's predefined constants which MAD-X lacks (ex. P0), as
        variables, when the lattice uses them"""
        import sirepo.template.madx

        n = set(v.name.lower() for v in madx.models.rpnVariables)
        u = set()
        for m in (
            madx.models.rpnVariables,
            madx.models.elements,
            madx.models.commands,
        ):
            for x in m:
                for v in x.values():
                    if isinstance(v, str):
                        u.update(t.lower() for t in re.findall(r"[A-Za-z_]\w*", v))
        for c in sorted(u):
            if (
                c in _OPAL_CONSTANTS
                and c not in sirepo.template.madx.MADX_CONSTANTS
                and c not in n
            ):
                madx.models.rpnVariables.insert(
                    0, PKDict(name=c, value=_OPAL_CONSTANTS[c])
                )

    def __madx_distribution(self, data):
        """OPAL's injected GAUSS distribution as the MAD-X beam's, the
        inverse of __fixup_distribution() and __dispersion()

        Returns:
            PKDict: distribution and dp_s_coupling, see _beam_to_madx(),
            empty when not a GAUSS distribution
        """
        d = LatticeUtil.find_first_command(data, "distribution")
        if not d or d.type != "GAUSS" or d.emitted == "1":
            pkdlog(
                "OPAL distribution type={} emitted={} has no MAD-X beam, not exported",
                d and d.type,
                d and d.emitted,
            )
            return PKDict()
        cv = code_var(data.models.rpnVariables)

        def _val(field):
            return cv.eval_var_with_assert(d[field])

        # sigma (beta * gamma) to sigma delta = sigma p / p
        sd = _val("sigmapz") / (self.particle_energy.beta * self.particle_energy.gamma)
        res = PKDict(
            # the bunch length in z to c * sigma t, sigma delta to sigma E / E
            sigt=_val("sigmaz") / self.particle_energy.beta,
            sige=sd * self.particle_energy.beta**2,
        )
        for dim in ("x", "y"):
            p = self.__madx_plane(dim, _val, sd)
            if not p:
                pkdlog("OPAL distribution has no {} emittance, not exported", dim)
                return PKDict()
            res.update(p)
        # a line, its twiss starts with the beam's
        return PKDict(
            distribution=res,
            dp_s_coupling=_val("corrz") or None,
        )

    def __madx_plane(self, dim, val, sigma_delta):
        """One plane of OPAL's GAUSS distribution as the MAD-X beam's, see
        __madx_distribution()

        Args:
            dim (str): x or y
            val (function): the distribution's field's value
            sigma_delta (float): sigma p / p
        Returns:
            PKDict: e<dim>, alpha_<dim>, beta_<dim>, and d<dim>, dp<dim>
            with dispersion; empty without an emittance
        """
        e = self.particle_energy
        v = PKDict(
            s=val(f"sigma{dim}"),
            # sigma (beta * gamma) to sigma x'
            sp=val(f"sigmap{dim}") / (e.beta * e.gamma),
            eta=0,
            etap=0,
        )
        if dim == "x" and sigma_delta:
            # OPAL has only horizontal dispersion
            v.eta = val("r61") * v.s / sigma_delta
            v.etap = val("r62") * v.sp / sigma_delta
        # second moments without the dispersion's
        v.xx = v.s**2 - (v.eta * sigma_delta) ** 2
        v.pp = v.sp**2 - (v.etap * sigma_delta) ** 2
        v.xp = val(f"corr{dim}") * v.s * v.sp - v.eta * v.etap * sigma_delta**2
        v.m = math.sqrt(max(v.xx * v.pp - v.xp**2, 0))
        if not v.m:
            return PKDict()
        res = PKDict(
            {
                f"e{dim}": v.m,
                f"alpha_{dim}": -v.xp / v.m if v.xp else 0.0,
                f"beta_{dim}": v.xx / v.m,
            }
        )
        if v.eta or v.etap:
            # with respect to delta to with respect to PT
            res[f"d{dim}"] = v.eta / e.beta
            res[f"dp{dim}"] = v.etap / e.beta
        return res

    def __multipole_fields(self, element_type):
        n = self._MULTIPOLE_ORDER[element_type]
        return (f"k{n}", f"k{n}s")

    def __normalize_opal_beam(self, data):
        b = LatticeUtil.find_first_command(data, "beam")
        cv = code_var(data.models.rpnVariables)
        self.beam = PKDict(
            {
                f: cv.eval_var_with_assert(b[f])
                for f in ("mass", "charge", "energy", "pc", "gamma")
            }
        )
        self.beam.mass = template_common.ParticleEnergy.get_mass(
            SIM_TYPE, b.particle, self.beam
        )
        self.beam.charge = template_common.ParticleEnergy.get_charge(
            SIM_TYPE, b.particle, self.beam
        )
        self.particle_energy = template_common.ParticleEnergy.compute_energy(
            SIM_TYPE,
            b.particle,
            self.beam.copy(),
        )

    def __rf_field_map(self, element):
        """OPAL 1DDynamic field map for a MAD-X RFCAVITY: whole pi mode
        cells of sin(kz) centered in its length, or a single gap of
        sin^2(pi z / l) when it is shorter than one cell (zero with zero
        slope at the ends, for the off-axis fields). OPAL scales the map's
        peak to VOLT [MV/m].

        Args:
            element (PKDict): RFCAVITY with l [m] and freq [MHz]
        Returns:
            PKDict: basename, content and gain, the on crest energy gain
            [MeV] per MV/m, for beta = 1 or for a gap the beam's beta, or
            None without l or freq
        """
        l = self._val(element.l)
        f = self._val(element.freq)
        if l <= 0 or f <= 0:
            return None
        w = template_common.ParticleEnergy.SPEED_OF_LIGHT / (f * 1e6)
        k = 2 * math.pi / w
        n = int(2 * l / w + 1e-9)
        p = max(400, math.ceil(self._RF_FIELD_MAP_POINTS * l / w))
        z = numpy.linspace(0, l, p + 1)
        if n:
            z0 = (l - n * w / 2) / 2
            e = numpy.where(
                (z >= z0) & (z <= z0 + n * w / 2), numpy.sin(k * (z - z0)), 0
            )
        else:
            e = numpy.sin(math.pi * z / l) ** 2
        return PKDict(
            basename=f"madx-rfcavity-{l:.10g}m-{f:.10g}MHz.txt",
            # z [cm], freq [MHz], an unused radial line, Ez
            content=f"1DDynamic {math.ceil(self._RF_FIELD_MAP_ACCURACY * p)}\n"
            + f"0 {l * 100:.10g} {p}\n{f:.10g}\n0 1 1\n"
            + "".join(f"{v:.10g}\n" for v in e),
            gain=(
                abs(numpy.trapezoid(e * numpy.exp(1j * k * z), z))
                if n
                else self._rf_gap_gain(l, f * 1e6, self.particle_energy.beta)
            ),
        )

    def __to_brho(self, value):
        # MAD-X normalized strength [1/m^(n+1)] to OPAL field [T/m^n]
        v = self._val(value)
        if v == 0:
            return 0
        if self.beam.charge < 0:
            v *= -1
        return "{} * {}".format(v, self._var_name("brho"))


def analysis_job_compute_particle_ranges(data, run_dir, **kwargs):
    return template_common.compute_field_range(
        data,
        _compute_range_across_frames,
        run_dir,
    )


def background_percent_complete(report, run_dir, is_running):
    def _percent(run_dir, spos):
        if not spos:
            return 0
        t = LatticeUtil.find_first_command(_SIM_DATA.sim_run_input(run_dir), "track")
        if t and isinstance(t.zstop, (int, float)):
            return spos * 100 / t.zstop
        return 0

    if is_running:
        c, p = read_frame_count(run_dir)
        return PKDict(
            frameCount=c - 1 if c > 0 else 0,
            percentComplete=_percent(run_dir, p),
        )
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if _SIM_DATA.sim_run_input(run_dir, checked=False):
        res.frameCount = read_frame_count(run_dir)[0]
        if res.frameCount > 0:
            return res.pkupdate(
                percentComplete=100,
                outputInfo=_output_info(run_dir),
            )
    return res


def bunch_plot(model, run_dir, frame_index, filename=OPAL_H5_FILE):
    def _points(file, frame_index, name):
        return numpy.array(file["/Step#{}/{}".format(frame_index, name)])

    def _title(file, frame_index):
        t = "Step {}".format(frame_index)
        if "SPOS" in file["/Step#{}".format(frame_index)].attrs:
            t += ", SPOS {0:.5f}m".format(
                file["/Step#{}".format(frame_index)].attrs["SPOS"][0]
            )
        return t

    return (
        hdf5_util.HDF5Util(str(run_dir.join(filename)))
        .heatmap(
            PKDict(
                format_plot=_units_from_hdf5,
                frame_index=frame_index,
                model=model,
                points=_points,
                title=_title,
            )
        )
        .pkupdate(threshold=[0])
    )


def code_var(variables):
    class _P(code_variable.PurePythonEval):
        # TODO(pjm): parse from opal files into schema
        _OPAL_PI = _OPAL_PI
        _OPAL_CONSTANTS = _OPAL_CONSTANTS

        def __init__(self):
            super().__init__(self._OPAL_CONSTANTS)

        def eval_var(self, expr, depends, variables):
            if re.match(r"^\{.+\}$", expr):
                # It is an array of values
                return expr, None
            return super().eval_var(expr, depends, variables)

    return code_variable.CodeVar(
        variables,
        _P(),
        case_insensitive=True,
    )


def get_data_file(run_dir, model, frame, options):
    if model in ("bunchAnimation", "plotAnimation") or "bunchReport" in model:
        return OPAL_H5_FILE
    if frame < 0:
        return template_common.text_data_file(OPAL_OUTPUT_FILE, run_dir)
    if model == "plot2Animation":
        return _OPAL_SDDS_FILE
    if model == "beamline3dAnimation":
        return _OPAL_VTK_FILE
    if "elementAnimation" in model:
        return _file_name_for_element_animation(
            PKDict(
                run_dir=run_dir,
                frameReport=model,
            )
        )
    raise AssertionError(f"unknown model={model}")


def new_simulation(data, new_simulation_data, qcall, **kwargs):
    data.models.simulation.elementPosition = new_simulation_data.elementPosition


def parse_opal_log(run_dir):
    return _OpalLogParser(run_dir, log_filename=OPAL_OUTPUT_FILE).parse_for_errors()


def post_execution_processing(success_exit, is_parallel, run_dir, **kwargs):
    if success_exit:
        return None
    return parse_opal_log(run_dir)


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
        return OpalMadxConverter(qcall=qcall).to_madx_text(data)
    return _generate_parameters_file(data, qcall=qcall)


def read_frame_count(run_dir):
    def _walk_file(h5file, key, step, res):
        if key:
            res[0] = step + 1
            res[1] = h5file[key].attrs["SPOS"][0]

    try:
        p = run_dir.join(OPAL_H5_FILE)
        if p.exists():
            return _iterate_hdf5_steps(p, _walk_file, [0, 0])[:2]
    except IOError:
        pass
    except RuntimeError:
        pass
    return 0, 0


def save_sequential_report_data(data, run_dir):
    report = data.models[data.report]
    res = None
    if "bunchReport" in data.report:
        res = bunch_plot(report, run_dir, 0)
        res.title = ""
    else:
        raise AssertionError("unknown report: {}".format(report))
    template_common.write_sequential_result(
        res,
        run_dir=run_dir,
    )


def sim_frame(frame_args):
    if "bunchAnimation" in frame_args.frameReport:
        return track_parser.bunch_comparison(frame_args, OPAL_H5_FILE)
    # elementAnimations
    return bunch_plot(
        frame_args,
        frame_args.run_dir,
        frame_args.frameIndex,
        _file_name_for_element_animation(frame_args),
    )


def sim_frame_beamline3dAnimation(frame_args):
    def _compute_3d_bounds(run_dir):
        res = []
        p = run_dir.join("data/opal_ElementPositions.txt")
        with pkio.open_text(p) as f:
            for line in f:
                m = re.search(r'^".*?"\s+(\S*?)\s+(\S*?)\s+(\S*?)\s*$', line)
                if m:
                    res.append([float(v) for v in (m.group(1), m.group(2), m.group(3))])
        res = numpy.array(res)
        bounds = []
        for n in range(3):
            v = res[:, n]
            bounds.append([min(v), max(v)])
        return bounds

    res = PKDict(
        title=" ",
        points=[],
        polys=[],
        colors=[],
        bounds=_compute_3d_bounds(frame_args.run_dir),
    )
    state = None
    with pkio.open_text(_OPAL_VTK_FILE) as f:
        for line in f:
            if line == "\n":
                continue
            if line.startswith("POINTS "):
                state = "points"
                continue
            if line.startswith("CELLS "):
                state = "polys"
                continue
            if line.startswith("CELL_TYPES"):
                state = None
                continue
            if line.startswith("COLOR_SCALARS"):
                state = "colors"
                continue
            if state == "points" or state == "colors":
                for v in line.split(" "):
                    res[state].append(float(v))
            elif state == "polys":
                for v in line.split(" "):
                    res[state].append(int(v))
    return res


def sim_frame_bunchAnimation(frame_args):
    a = frame_args.sim_in.models.bunchAnimation
    a.update(frame_args)
    return bunch_plot(a, a.run_dir, a.frameIndex)


def sim_frame_comparisonAnimation(frame_args):
    return track_parser.beam_comparison(frame_args, _OPAL_SDDS_FILE)


def sim_frame_plotAnimation(frame_args):
    def _walk_file(h5file, key, step, res):
        if key:
            for field in res.values():
                field.points.append(h5file[key].attrs[field.name][field.index])
        else:
            for field in res.values():
                _units_from_hdf5(h5file, field)

    return hdf5_util.HDF5Util(frame_args.run_dir.join(OPAL_H5_FILE)).lineplot(
        PKDict(
            model=frame_args,
            index=lambda parts: _DIM_INDEX[parts[1]] if len(parts) > 1 else 0,
            format_plots=lambda h5file, plots: _iterate_hdf5_steps_from_handle(
                h5file,
                _walk_file,
                plots,
            ),
            y_fields=("y1", "y2", "y3", "y4", "y5"),
        )
    )


def sim_frame_plot2Animation(frame_args):
    def _format_col_name(name):
        return name.replace(" ", "_")

    def _format_plot(plot, sdds_units):
        _field_units(sdds_units, plot)

    return sdds_util.SDDSUtil(str(frame_args.run_dir.join(_OPAL_SDDS_FILE))).lineplot(
        PKDict(
            format_col_name=_format_col_name,
            format_plot=_format_plot,
            model=template_common.model_from_frame_args(frame_args),
            dynamicYLabel=True,
            y_fields=("y1", "y2", "y3", "y4", "y5"),
        )
    )


def stateful_compute_convert_lattice(data, **kwargs):
    return PKDict(
        imported_data=sirepo.template.madx_converter.convert_lattice(
            data, data.args.toSimType
        )
    )


def stateful_compute_import_file(data, **kwargs):
    from sirepo.template import elegant
    from sirepo.template import opal_parser

    if data.args.ext_lower == ".in":
        res, input_files = opal_parser.parse_file(
            data.args.file_as_str,
            filename=data.args.basename,
        )
    elif data.args.ext_lower == ".madx" or data.args.ext_lower == ".seq":
        res = OpalMadxConverter(qcall=None).from_madx_text(data.args.file_as_str)
        res.models.simulation.name = data.args.purebasename
    elif data.args.ext_lower == ".ele":
        return elegant.elegant_file_import(data)
    elif data.args.ext_lower == ".lte":
        res = OpalMadxConverter(None).from_madx_text(
            elegant.ElegantMadxConverter(qcall=None).to_madx_text(
                elegant.elegant_file_import(data).imported_data
            )
        )
    else:
        # handle TRACK specific datafiles
        res = track_parser.import_file(
            data.args.basename.lower(),
            data.args.file_as_str,
            data.args.pkunchecked_nested_get("import_file_arguments"),
        )
        if res and "importState" in res and res.importState == "needLattice":
            return res
    if not res:
        raise IOError(
            f"invalid file={data.args.basename} extension, expecting .in, .ele, .lte or .madx"
        )
    _default_lattice_overlay(res)
    return PKDict(imported_data=res)


def update_export(data, z, qcall):
    track_parser.update_export(data, z, qcall)


def validate_file(file_type, path, sim_id, qcall):
    return track_parser.validate_file(file_type, path, sim_id, qcall)


def write_parameters(data, run_dir, is_parallel):
    track_parser.write_parameters(data, run_dir, is_parallel)
    pkio.write_text(
        run_dir.join(OPAL_INPUT_FILE),
        _generate_parameters_file(data),
    )
    if is_parallel:
        pkio.write_text(
            run_dir.join(OPAL_POSITION_FILE),
            "import os\n"
            + 'os.system("python data/opal_ElementPositions.py --export-vtk")\n',
        )


class _Generate(sirepo.lib.GenerateBase):
    def __init__(self, data, qcall=None):
        self.data = data
        self.qcall = qcall
        self._schema = SCHEMA

    def sim(self):
        d = self.data
        self.jinja_env = template_common.flatten_data(d.models, PKDict())
        self._code_var = code_var(d.models.rpnVariables)
        if "bunchReport" in d.get("report", ""):
            return self._bunch_simulation()
        return self._full_simulation()

    def _bunch_simulation(self):
        v = self.jinja_env
        # keep only first distribution and beam in command list
        beam = LatticeUtil.find_first_command(self.data, "beam")
        distribution = LatticeUtil.find_first_command(self.data, "distribution")
        v.beamName = beam.name
        v.distributionName = distribution.name
        # these need to get set to default or distribution won't generate in 1 step
        # for emitted distributions
        distribution.nbin = 0
        distribution.emissionsteps = 1
        self.data.models.commands = [
            LatticeUtil.find_first_command(self.data, "option"),
            beam,
            distribution,
        ]
        self._generate_commands_and_variables()
        return template_common.render_jinja(SIM_TYPE, v, "bunch.in")

    def _format_field_value(self, state, model, field, el_type):
        value = model[field]
        if el_type == "Boolean":
            value = "true" if value == "1" else "false"
        elif el_type == "RPNValue":
            value = _fix_opal_float(value)
        elif el_type == "InputFile":
            value = self._input_file(
                LatticeUtil.model_name_for_data(model), field, value
            )
        elif el_type == "OutputFile":
            value = self._output_file(model, field)
        elif re.search(r"List$", el_type):
            value = state.id_map[int(value)].name
        elif re.search(r"String", el_type):
            if str(value):
                if not re.search(r"^\s*\{.*\}$", value):
                    value = '"{}"'.format(value)
        elif LatticeUtil.is_command(model):
            if el_type != "RPNValue" and str(value):
                value = '"{}"'.format(value)
        elif not LatticeUtil.is_command(model):
            if model.type in _ELEMENTS_WITH_TYPE_FIELD and "_type" in field:
                return ["type", value]
        if str(value):
            return [field, value]
        return None

    def _full_simulation(self):
        v = self.jinja_env
        v.lattice = self._generate_lattice(
            self.util,
            self._code_var,
            LatticeUtil.find_first_command(
                self.util.data,
                "track",
            ).line
            or self.util.select_beamline().id,
        )
        v.use_beamline = self.util.select_beamline().name
        self._generate_commands_and_variables()
        return template_common.render_jinja(SIM_TYPE, v, "parameters.in")

    def _generate_commands(self, util, is_header):
        # reorder command so OPTION and list commands come first
        commands = []
        key = None
        if is_header:
            key = "header_commands"
            # add header commands in order, with option first
            for ctype in _HEADER_COMMANDS:
                for c in util.data.models.commands:
                    if c._type == ctype:
                        commands.append(c)
        else:
            key = "other_commands"
            for c in util.data.models.commands:
                if c._type not in _HEADER_COMMANDS:
                    commands.append(c)
        util.data.models[key] = commands
        res = util.render_lattice(
            util.iterate_models(
                OpalElementIterator(self._format_field_value),
                key,
            ).result,
            quote_name=True,
            want_semicolon=True,
        )
        # separate run from track, add endtrack
        # TODO(pjm): better to have a custom element generator for this case
        lines = []
        for line in res.splitlines():
            m = re.match("(.*?: track,.*?)(run_.*?)(;|,[^r].*)", line)
            if m:
                lines.append("{}{}".format(re.sub(r",$", "", m.group(1)), m.group(3)))
                lines.append(" run, {};".format(re.sub(r"run_", "", m.group(2))))
                lines.append("endtrack;")
            else:
                lines.append(line)
        return "\n".join(lines)

    def _generate_commands_and_variables(self):
        self.jinja_env.update(
            dict(
                variables=self._code_var.generate_variables(self._generate_variable),
                header_commands=self._generate_commands(self.util, True),
                commands=self._generate_commands(self.util, False),
            )
        )

    def _generate_lattice(self, util, code_var, beamline_id):
        if util.data.models.simulation.elementPosition == "absolute":
            beamline, visited = _generate_absolute_beamline(util, beamline_id)
        else:
            beamline, _, names, visited = _generate_beamline(
                util, code_var, beamline_id
            )
            beamline += "{}: LINE=({});\n".format(
                util.id_map[beamline_id].name,
                ",".join(names),
            )
        res = (
            util.render_lattice(
                util.iterate_models(
                    OpalElementIterator(self._format_field_value, visited),
                    "elements",
                ).result,
                quote_name=True,
                want_semicolon=True,
            )
            + "\n"
        )
        res += beamline
        return res

    def _generate_variable(self, name, variables, visited):
        res = ""
        if name not in visited:
            res += "REAL {} = {};\n".format(name, _fix_opal_float(variables[name]))
            visited[name] = True
        return res

    def _input_file(self, model_name, field, filename):
        return '"{}"'.format(
            _SIM_DATA.lib_file_name_with_model_field(
                model_name,
                field,
                filename,
            )
        )

    def _output_file(self, model, field):
        ext = "dat" if model.get("_type", "") == "list" else "h5"
        return '"{}.{}.{}"'.format(model.name, field, ext)


def _compute_range_across_frames(run_dir, **kwargs):
    def _walk_file(h5file, key, step, res):
        if key:
            for field in res:
                v = numpy.array(h5file["/{}/{}".format(key, field)])
                min1, max1 = v.min(), v.max()
                if res[field]:
                    if res[field][0] > min1:
                        res[field][0] = min1
                    if res[field][1] < max1:
                        res[field][1] = max1
                else:
                    res[field] = [min1, max1]

    res = PKDict()
    for v in SCHEMA.enum.PhaseSpaceCoordinate:
        res[v[0]] = None
    return _iterate_hdf5_steps(run_dir.join(OPAL_H5_FILE), _walk_file, res)


def _default_lattice_overlay(data):
    """An imported simulation's Beam Statistics shows the lattice, unless
    its beamlines are positioned (absolute positioning), which the overlay
    doesn't show"""
    if data.models.simulation.get("elementPosition") == "absolute" and any(
        b.get(f) for b in data.models.beamlines for f in _BEAMLINE_POSITION_FIELDS
    ):
        return
    data.models.setdefault("plot2Animation", PKDict()).includeLattice = "1"


def _field_units(units, field):
    if units == "1":
        units = ""
    elif units[0] == "M" and len(units) > 1:
        units = re.sub(r"^.", "", units)
        field.points = (numpy.array(field.points) * 1e6).tolist()
    elif units[0] == "G" and len(units) > 1:
        units = re.sub(r"^.", "", units)
        field.points = (numpy.array(field.points) * 1e9).tolist()
    elif units == "ns":
        units = "s"
        field.points = (numpy.array(field.points) / 1e9).tolist()
    if units:
        if re.search(r"^#", units):
            field.label += " ({})".format(units)
        else:
            field.label += " [{}]".format(units)
    field.units = units


def _file_name_for_element_animation(frame_args):
    r = frame_args.frameReport
    for info in _output_info(frame_args.run_dir):
        if info.modelKey == r:
            return info.filename
    raise AssertionError(f"no output for frameReport={r}")


def _find_run_method(commands):
    for command in commands:
        if command._type == "track" and command.run_method:
            return command.run_method
    return "THIN"


def _fix_opal_float(value):
    if value and not code_variable.CodeVar.is_var_value(value):
        # need to format values as floats, OPAL has overflow issues with large integers
        return float(value)
    return value


def _generate_absolute_beamline(util, beamline_id, count_by_name=None, visited=None):
    if count_by_name is None:
        count_by_name = PKDict()
    if visited is None:
        visited = set()
    names = []
    res = ""
    beamline = util.id_map[abs(beamline_id)]
    items = beamline["items"]
    for idx in range(len(items)):
        item_id = items[idx]
        item = util.id_map[abs(item_id)]
        name = item.name.upper()
        if name not in count_by_name:
            count_by_name[name] = 0
        if "type" in item:
            # element
            name = '"{}#{}"'.format(name, count_by_name[name])
            count_by_name[item.name.upper()] += 1
            pos = beamline.positions[idx]
            res += '{}: "{}",elemedge={};\n'.format(
                name, item.name.upper(), pos.elemedge
            )
            names.append(name)
            visited.add(item_id)
        else:
            if item_id not in visited:
                text, visited = _generate_absolute_beamline(
                    util, item_id, count_by_name, visited
                )
                res += text
            names.append("{}".format(name))

    has_orientation = False
    for f in ("x", "y", "z", "theta", "phi", "psi"):
        if f in beamline and beamline[f]:
            has_orientation = True
            break
    orientation = ""
    if has_orientation:
        orientation = ", ORIGIN={}, ORIENTATION={}".format(
            "{}{}, {}, {}{}".format("{", beamline.x, beamline.y, beamline.z, "}"),
            "{}{}, {}, {}{}".format(
                "{", beamline.theta, beamline.phi, beamline.psi, "}"
            ),
        )
    res += "{}: LINE=({}){};\n".format(
        beamline.name,
        ",".join(names),
        orientation,
    )
    return res, visited


def _generate_beamline(
    util, code_var, beamline_id, count_by_name=None, edge=0, names=None, visited=None
):
    if count_by_name is None:
        count_by_name = PKDict()
    if names is None:
        names = []
    if visited is None:
        visited = set()
    res = ""
    run_method = _find_run_method(util.data.models.commands)
    beamline = util.id_map[abs(beamline_id)]
    items = beamline["items"]
    if beamline_id < 0:
        items = list(reversed(items))
    for idx in range(len(items)):
        item_id = items[idx]
        item = util.id_map[abs(item_id)]
        if "type" in item:
            # element
            name = item.name.upper()
            if name not in count_by_name:
                count_by_name[name] = 0
            name = '"{}#{}"'.format(name, count_by_name[name])
            count_by_name[item.name.upper()] += 1
            if run_method == "OPAL-CYCL" or run_method == "CYCLOTRON-T":
                res += '"{}": {};\n'.format(name, item.name.upper())
                names.append(name)
                visited.add(item_id)
                continue
            length = code_var.eval_var(item.l)[0]
            if item.type == "DRIFT" and length < 0:
                # don't include reverse drifts, for positioning only
                pass
            else:
                res += '{}: "{}",elemedge={};\n'.format(name, item.name.upper(), edge)
                names.append(name)
                if item.type == "SBEND":
                    # SBEND's l is its chord, but elemedge is along the
                    # design path, the arc (verified with OPAL-T's
                    # ElementPositions)
                    angle = code_var.eval_var_with_assert(item.angle)
                    if angle:
                        length = angle * length / (2 * math.sin(angle / 2))
                visited.add(item_id)
            edge += length
        else:
            # beamline
            # a sub-beamline of a reversed beamline is reversed in turn
            text, edge, names, visited = _generate_beamline(
                util,
                code_var,
                -item_id if beamline_id < 0 else item_id,
                count_by_name,
                edge,
                names,
                visited,
            )
            res += text
    return res, edge, names, visited


def _generate_parameters_file(data, qcall=None):
    return _Generate(data, qcall=qcall).sim()


def _iterate_hdf5_steps(path, callback, state):
    def _read(file_obj):
        _iterate_hdf5_steps_from_handle(file_obj, callback, state)

    hdf5_util.HDF5Util(str(path)).read_while_writing(_read)
    return state


def _iterate_hdf5_steps_from_handle(h5file, callback, state):
    step = 0
    key = "Step#{}".format(step)
    while key in h5file:
        callback(h5file, key, step, state)
        step += 1
        key = "Step#{}".format(step)
    callback(h5file, None, -1, state)


def _output_info(run_dir):
    data = _SIM_DATA.sim_run_input(run_dir)
    files = LatticeUtil(data, SCHEMA).iterate_models(OpalOutputFileIterator()).result
    res = []
    for k in files.keys_in_order:
        if run_dir.join(files[k]).exists():
            res.append(
                PKDict(
                    modelKey="elementAnimation{}".format(k),
                    filename=files[k],
                    isHistogram=True,
                )
            )
    return res


def _units_from_hdf5(h5file, field):
    return _field_units(
        pkcompat.from_bytes(h5file.attrs["{}Unit".format(field.name)]), field
    )
