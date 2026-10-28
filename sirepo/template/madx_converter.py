# -*- coding: utf-8 -*-
"""Convert codes to/from MAD-X.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import madx_parser
from sirepo.template.lattice import LatticeUtil
from sirepo.template.template_common import ParticleEnergy
import copy
import math
import numpy
import re
import scipy.constants
import sirepo.sim_data
import sirepo.template


def convert_lattice(data, to_sim_type):
    """Convert elegant, MAD-X, OPAL or RF-Track `data` to another of those
    codes, the same way as exporting a MAD-X lattice and importing it.

    Args:
        data (PKDict): simulationType and models of the source simulation
        to_sim_type (str): target code
    Returns:
        PKDict: the target simulation's data
    """
    from sirepo import feature_config
    from sirepo.template import madx

    f = data.simulationType
    if (
        f == to_sim_type
        or f not in feature_config.LATTICE_CONVERSION_CODES
        or to_sim_type not in feature_config.LATTICE_CONVERSION_CODES
    ):
        raise AssertionError(f"invalid conversion from={f} to={to_sim_type}")
    if f == madx.SIM_TYPE:
        t = madx.python_source_for_model(data, model=None, qcall=None)
    elif to_sim_type == madx.SIM_TYPE:
        res = _converter(f).to_madx(data)
    else:
        t = _converter(f).to_madx_text(data)
    if to_sim_type != madx.SIM_TYPE:
        res = _converter(to_sim_type).from_madx_text(t)
    res.models.simulation.name = data.models.simulation.name
    return res


def initial_twiss(madx, values=None):
    """A MAD-X twiss command's initial values, when it has none: the twiss
    of a line

    Args:
        madx (PKDict): MAD-X data, modified
        values (PKDict): alpha_x, beta_x, alpha_y, beta_y and optional dx,
            dpx, dy, dpy, default the beam's variables (sr_alpha_x, ...,
            sr_dx, ...)
    """
    t = LatticeUtil.find_first_command(madx, "twiss")
    if not t or any(t.get(f) not in (None, "", 0, "0") for f in ("betx", "bety")):
        return
    for d in ("x", "y"):
        for f, m in (("alpha", "alf"), ("beta", "bet")):
            t[f"{m}{d}"] = values[f"{f}_{d}"] if values else f"sr_{f}_{d}"
    n = set(v.name for v in madx.models.rpnVariables)
    for f in MadxConverter._BEAM_DISPERSION_VARS:
        if values:
            if f in values:
                t[f] = values[f]
        elif f"sr_{f}" in n:
            t[f] = f"sr_{f}"


class MadxConverter:
    # Settings: each converter sets those it needs and MadxConverter reads
    # them, so a converter needn't use them itself.
    #: from_madx(): the code's own constants, see fill_in_missing_constants()
    _CONSTANTS = PKDict()
    #: from_madx(): the bend types MAD-X DIPEDGEs are merged into, see
    #: _merge_dipedges()
    _DIPEDGE_BENDS = ()
    #: from_madx_text(): MAD-X's variable names in lower case, see
    #: madx_parser.parse_file()
    _DOWNCASE_VARIABLES = False
    #: from_madx(): the simulation's elementPosition, when the code has it
    _ELEMENT_POSITION = None
    #: from_madx(): remove zero length drifts, see _remove_zero_drifts()
    _REMOVE_ZERO_DRIFTS = False
    #: from_madx(): give thin RF cavities a length, see
    #: _thicken_thin_cavities()
    _THICKEN_THIN_CAVITIES = False
    #: the code's element types: [MAD-X element type, field, ...], a field
    #: being the same name in both or "code field=MAD-X field"; a field is
    #: copied unchanged when the element has it, then
    #: _from_madx_<MAD-X type>() or _to_madx_<code type>() is called, if
    #: defined, for any other conversion (ex. units)
    _ELEMENTS = PKDict()
    #: MAD-X element type: the code element type made from it, see
    #: _ELEMENTS, or None when it isn't copied (ex. DIPEDGE, which
    #: _merge_dipedges() merges into the bend beside it)
    _FROM_MADX = PKDict()
    #: _merge_dipedge(): a DIPEDGE's fields to the bend's, per edge
    _DIPEDGE_FIELDS = PKDict(entrance=PKDict(e1="e1"), exit=PKDict(e1="e2"))
    #: _merge_dipedge(): the bend's field for the DIPEDGE's hgap, and its
    #: multiple of hgap
    _DIPEDGE_GAP = ("hgap", 1)
    #: the beam's dispersion at the start (MAD-X's, with respect to PT), as
    #: variables sr_dx, ...
    _BEAM_DISPERSION_VARS = ("dpx", "dpy", "dx", "dy")
    #: the beam's twiss at the start, as variables sr_alpha_x, ...
    _BEAM_TWISS_VARS = ("alpha_x", "alpha_y", "beta_x", "beta_y")
    #: the beam's twiss is the lattice's periodic twiss when 1, see
    #: madx._bunch_vars()
    _MATCH_TWISS_VAR = "match_twiss_parameters"
    #: the macro-particle count, as variable sr_n_particles_per_bunch
    _PARTICLE_COUNT_VAR = "n_particles_per_bunch"
    #: MAD-X particle to the code's; any other is given by mass and charge
    _PARTICLE_MAP = PKDict()
    #: MAD-X's RF cavities are on crest at this lag for any particle
    #: (verified by tracking in MAD-X and PTC)
    _MADX_CREST_LAG = 0.25
    _MADX_VARIABLES = PKDict(
        twopi="pi * 2",
        raddeg="pi / 180",
        degrad="180 / pi",
    )
    #: length [m] given to zero length RF cavities by
    #: _thicken_thin_cavities(), short of the beam's transit time but long
    #: beside the beam's radius, as the field map codes' off-axis fields
    #: are expansions in r / length
    _THIN_CAVITY_LENGTH = 0.03

    def __init__(self, sim_type, qcall=None):
        self.sim_type = sim_type
        self.qcall = qcall

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # a handler which no element type reaches, ex. a misspelled type
        for n in dir(cls):
            m = re.search(r"^_(from|to)_madx_(\w+)$", n)
            if m and m.group(2).upper() not in (
                cls._FROM_MADX if m.group(1) == "from" else cls._ELEMENTS
            ):
                pkdlog("{} {} matches no element type", cls.__name__, n)

    def fill_in_missing_constants(self, data, constants):
        import sirepo.template.madx
        import ast

        class Visitor(ast.NodeVisitor):
            def visit_Name(self, node):
                return node.id

        n = [v.name for v in data.models.rpnVariables]
        for v in data.models.rpnVariables:
            values = set()
            if type(v.value) == str:
                tree = ast.parse(v.value)
                for node in ast.walk(tree):
                    values.add(Visitor().visit(node))
            for c in sirepo.template.madx.MADX_CONSTANTS.keys() - constants.keys():
                if type(v.value) == str and c in values and c not in n:
                    data.models.rpnVariables.insert(
                        0, PKDict(name=c, value=sirepo.template.madx.MADX_CONSTANTS[c])
                    )
                    n.append(c)
        return data

    def from_madx(self, data):
        """MAD-X `data` as the code's: the elements and beamlines, then the
        steps the class attributes select (_CONSTANTS, ...), the elements
        the handlers insert (_inserts), then _fixup_from_madx() with the
        beam, see __beam_from_madx()"""
        from sirepo.template import madx

        self.__init_direction(data, madx.SIM_TYPE, self.sim_type)
        self._inserts = PKDict()
        if self._THICKEN_THIN_CAVITIES:
            self._thicken_thin_cavities(data)
        res = self.fill_in_missing_constants(
            self._convert(self.__normalize_madx_beam(data)), self._CONSTANTS
        )
        if self._ELEMENT_POSITION:
            res.models.simulation.elementPosition = self._ELEMENT_POSITION
        if self._REMOVE_ZERO_DRIFTS:
            self._remove_zero_drifts(res)
        if self._DIPEDGE_BENDS:
            self._merge_dipedges(data, res, self._DIPEDGE_BENDS)
        self._insert_elements(res, self._inserts)
        self._fixup_from_madx(data, res, self.__beam_from_madx(data))
        return res

    def from_madx_text(self, text):
        return self.from_madx(madx_parser.parse_file(text, self._DOWNCASE_VARIABLES))

    def to_madx(self, data):
        from sirepo.template import madx

        self.__init_direction(data, self.sim_type, madx.SIM_TYPE)
        self._inserts = PKDict()
        res = self._convert(data)
        self._insert_elements(res, self._inserts)
        b = self._beam_to_madx(data, res)
        if b:
            self.__beam_to_madx(res, b)
        return res

    def to_madx_text(self, data):
        from sirepo.template import madx

        return madx.python_source_for_model(
            self.to_madx(data),
            model=None,
            qcall=self.qcall,
        )

    def _aperture(self, element):
        """MAD-X element's aperture as PKDict(apertype, x, y) of half widths
        [m], y is x for a circle or a single value; None if unset
        """
        a = self._aperture_values(element)
        if not a:
            return None
        t = str(element.get("apertype") or "circle").lower()
        return PKDict(
            apertype=t,
            x=a[0],
            y=a[0] if t == "circle" or len(a) == 1 else a[1],
        )

    def _aperture_values(self, element):
        """MAD-X element's aperture, ex. "{0.01, 0.02}", as evaluated
        values; empty if unset (all zeros, the default)
        """
        res = self._array_values(element.get("aperture", ""))
        return res if any(res) else []

    def _array_text(self, values):
        """MAD-X array from `values`, ex. "{0.0, 0.1}" (no "-0.0")"""
        return "{" + ", ".join(str(v + 0.0) for v in values) + "}"

    def _array_values(self, value):
        """MAD-X array, ex. "{0.01, 2 * a}", as evaluated values"""
        v = str(value).strip("{} ")
        return [
            self._val(x.strip())
            for x in (v.split(",") if "," in v else v.split())
            if x.strip()
        ]

    def _beam_dispersion(self, madx):
        """The beam's dispersion variables present in `madx`, see
        _BEAM_DISPERSION_VARS

        Returns:
            PKDict: ex. dx=value
        """
        res = PKDict()
        for f in self._BEAM_DISPERSION_VARS:
            v = self._find_var(madx, f)
            if v:
                res[f] = v.value
        return res

    def _beam_to_madx(self, data, madx):
        """The code's beam for to_madx(), see __beam_to_madx()

        Returns:
            PKDict: None without a beam
        """
        return None

    def _beam_twiss(self, madx):
        """The beam's twiss variables present in `madx`, see
        _BEAM_TWISS_VARS

        Returns:
            PKDict: ex. alpha_x=value
        """
        res = PKDict()
        for f in self._BEAM_TWISS_VARS:
            v = self._find_var(madx, f)
            if v:
                res[f] = v.value
        return res

    def _convert(self, data):
        self.result = simulation_db.default_data(self.to_class.sim_type())
        self._copy_beamlines(data)
        self._copy_elements(data)
        self._copy_code_variables(data)
        LatticeUtil(
            self.result,
            self.to_class.schema(),
        ).sort_elements_and_beamlines()
        return self.result

    def _copy_beamlines(self, data):
        for bl in data.models.beamlines:
            b = PKDict(
                name=bl.name,
                items=bl["items"],
                id=bl.id,
            )
            # the target's beamline fields, ex. OPAL's x, y, z, theta, phi,
            # psi, which a converted (current version) sim isn't fixed up for
            self.to_class.update_model_defaults(b, "beamline")
            self.result.models.beamlines.append(b)
        for f in ("name", "visualizationBeamlineId", "activeBeamlineId"):
            if f in data.models.simulation:
                self.result.models.simulation[f] = data.models.simulation[f]

    def _copy_code_variables(self, data):
        res = copy.deepcopy(data.models.rpnVariables)
        if self.to_class.sim_type() in ("madx", "opal"):
            res = [
                v
                for v in res
                if v.name not in self._MADX_VARIABLES and not self.__is_builtin(v)
            ]
        else:
            names = set([v.name for v in res])
            for name in self._MADX_VARIABLES:
                if name not in names:
                    res.append(
                        PKDict(
                            name=name,
                            value=self._MADX_VARIABLES[name],
                        )
                    )
        self.result.models.rpnVariables = res

    def _copy_elements(self, data):
        for e in data.models.elements:
            r = self.__copy_element(copy.deepcopy(e))
            if r:
                self.result.models.elements.append(r)

    def _crest_offset(self, lag):
        """MAD-X RF `lag` [turns] as the phase offset from crest [turns],
        in [-0.5, 0.5)"""
        res = (self._val(lag) - self._MADX_CREST_LAG) % 1
        return res - 1 if res >= 0.5 else res

    def _find_var(self, data, name):
        name = self._var_name(name)
        for v in data.models.rpnVariables:
            if v.name == name:
                return v
        return None

    def _fixup_element(self, element_in, element_out):
        pass

    def _fixup_from_madx(self, madx, data, beam):
        """The code's own steps after from_madx()'s, ex. its beam from
        `beam`, see __beam_from_madx()"""
        pass

    def _insert_elements(self, data, inserts):
        """Add new elements beside existing ones in every beamline.
        `inserts` maps an existing element's _id to PKDict(before=[...],
        after=[...]) of new elements; an element may be used more than
        once.
        """
        for i, v in inserts.items():
            for e in v.get("before", []) + v.get("after", []):
                if "_id" not in e:
                    e._id = LatticeUtil.max_id(data) + 1
                    self.to_class.update_model_defaults(e, e.type)
                    data.models.elements.append(e)
        for bl in data.models.beamlines:
            items = []
            for item in bl["items"]:
                v = inserts.get(item, PKDict())
                items.extend(e._id for e in v.get("before", []))
                items.append(item)
                items.extend(e._id for e in v.get("after", []))
            bl["items"] = items

    def _is_beam_value_set(self, field):
        """Is the MAD-X beam's `field` (ex. sigt) other than the MAD-X
        schema's default? Defaults such as ex=1 [m] or sigt=1 [m] are
        placeholders the parser fills in, not part of the beam. sige's
        default, 1e-3, is a real energy spread, so it is always set.
        """
        if field == "sige":
            return True
        return (
            self._val(self.beam[field])
            != self.from_class.schema().model.command_beam[field][2]
        )

    def _is_twiss_matched(self, madx):
        """Is the beam's twiss the lattice's periodic twiss? see
        _MATCH_TWISS_VAR"""
        v = self._find_var(madx, self._MATCH_TWISS_VAR)
        return bool(v and self._val(v.value))

    def _lag_from_crest_offset(self, offset):
        """MAD-X RF lag [turns] for the phase `offset` [turns] from crest"""
        return (offset + self._MADX_CREST_LAG) % 1

    def _madx_beam(self, madx, particle, mass, charge, pc, beam=None):
        """Set the MAD-X beam (to_madx), its energy by pc

        Args:
            madx (PKDict): MAD-X data
            particle (str): MAD-X particle, "other" by mass and charge, see
                _madx_particle
            mass (float): [GeV]
            charge (float): [e]
            pc (float): [GeV/c]
            beam (PKDict): optional distribution, see _madx_distribution
        Returns:
            PKDict: MAD-X beam command
        """
        res = LatticeUtil.find_first_command(madx, "beam")
        if particle == "other":
            particle = self._madx_particle(mass, charge)
        res.particle = particle
        if particle == "other":
            res.mass = mass
            res.charge = charge
        res.energy = 0
        res.pc = pc
        madx.models.bunch.beamDefinition = "pc"
        if beam:
            self._madx_distribution(madx, beam)
        return res

    def _madx_distribution(self, madx, beam):
        """Set the MAD-X beam's distribution and the bunch (to_madx)

        Args:
            madx (PKDict): MAD-X data
            beam (PKDict): ex, ey [m], sigt (c * sigma t [m]), sige (sigma
                E / E), and alpha_x, beta_x, alpha_y, beta_y as the bunch's
                twiss and its variables; without them, the bunch is matched
                to the lattice's periodic twiss; optional dx, dpx, dy, dpy,
                the bunch's dispersion (with respect to PT) and its
                variables
        """
        res = LatticeUtil.find_first_command(madx, "beam")
        res.pkupdate(ex=beam.ex, ey=beam.ey, sigt=beam.sigt, sige=beam.sige)
        if not all(f in beam for f in self._BEAM_TWISS_VARS):
            madx.models.bunch.matchTwissParameters = "1"
            return
        for dim in ("x", "y"):
            for f, m in (("alpha", "alf"), ("beta", "bet")):
                v = beam[f"{f}_{dim}"]
                self._replace_var(madx, f"{f}_{dim}", v)
                madx.models.bunch[f"{m}{dim}"] = self._val(v)
            self._replace_var(
                madx,
                f"gamma_{dim}",
                "(1 + {} * {}) / {}".format(
                    self._var_name(f"alpha_{dim}"),
                    self._var_name(f"alpha_{dim}"),
                    self._var_name(f"beta_{dim}"),
                ),
            )
        for f in self._BEAM_DISPERSION_VARS:
            if f in beam:
                self._replace_var(madx, f, beam[f])
                madx.models.bunch[f] = self._val(beam[f])

    def _madx_particle(self, mass, charge):
        """MAD-X's named particle (not ion) with `mass` [GeV] and `charge`
        [e], ex. a code's custom antiproton, or "other"
        """
        for k, v in self.to_class.schema().constants.particleMassAndCharge.items():
            if k != "ion" and v[1] == charge and math.isclose(v[0], mass, rel_tol=1e-6):
                return k
        return "other"

    def _merge_dipedge(self, bend, dipedge, is_entrance):
        """Merge MAD-X `dipedge` into the converted `bend`'s entrance or
        exit, see _DIPEDGE_FIELDS and _DIPEDGE_GAP; a field the bend's type
        lacks is skipped
        """
        m = self.to_class.schema().model[bend.type]
        for f, b in self._DIPEDGE_FIELDS["entrance" if is_entrance else "exit"].items():
            if b in m:
                bend[b] = dipedge[f]
        if self._val(dipedge.hgap):
            f, s = self._DIPEDGE_GAP
            bend[f] = dipedge.hgap if s == 1 else s * self._val(dipedge.hgap)

    def _merge_dipedges(self, madx, data, bend_types):
        """Remove the converted MAD-X DIPEDGE elements, merging each into the
        bend (of `bend_types`) right before or after it in a beamline, with
        `_merge_dipedge()`. A DIPEDGE between two bends is the first's exit.
        """
        dipedges = PKDict(
            {e._id: e for e in madx.models.elements if e.type == "DIPEDGE"}
        )
        if not dipedges:
            return
        data.models.elements = [
            e for e in data.models.elements if e._id not in dipedges
        ]
        bends = PKDict({e._id: e for e in data.models.elements if e.type in bend_types})
        for bl in data.models.beamlines:
            items = bl["items"]
            for i, item in enumerate(items):
                if item not in dipedges:
                    continue
                if i > 0 and items[i - 1] in bends:
                    self._merge_dipedge(
                        bends[items[i - 1]], dipedges[item], is_entrance=False
                    )
                elif i + 1 < len(items) and items[i + 1] in bends:
                    self._merge_dipedge(
                        bends[items[i + 1]], dipedges[item], is_entrance=True
                    )
            bl["items"] = [i for i in items if i not in dipedges]

    def _particle_count(self, madx):
        """The macro-particle count variable's value, see _PARTICLE_COUNT_VAR

        Returns:
            int: None if `madx` has none
        """
        v = self._find_var(madx, self._PARTICLE_COUNT_VAR)
        return int(round(float(self._val(v.value)))) if v else None

    def _particle_from_madx(self, particle):
        """The code's name for MAD-X's `particle`, see _PARTICLE_MAP

        Returns:
            str: None when given by mass and charge
        """
        return self._PARTICLE_MAP.get(particle)

    def _particle_to_madx(self, particle):
        """MAD-X's name for the code's `particle`, "other" (by mass and
        charge) when it has none"""
        return {v: k for k, v in self._PARTICLE_MAP.items()}.get(particle, "other")

    def _set_particle_count(self, madx, count):
        """The macro-particle `count` as the variable and the MAD-X bunch's
        numberOfParticles, within its limits (to_madx)"""
        n = int(round(float(count)))
        self._replace_var(madx, self._PARTICLE_COUNT_VAR, n)
        s = self.to_class.schema().model.bunch.numberOfParticles
        madx.models.bunch.numberOfParticles = min(max(n, s[4]), s[5])
        if madx.models.bunch.numberOfParticles != n:
            pkdlog(
                "particle count={} limited to MAD-X's {}",
                n,
                madx.models.bunch.numberOfParticles,
            )

    def _remove_zero_drifts(self, data):
        z = set()
        e = []
        for el in data.models.elements:
            if el.type == "DRIFT" and el.l == 0:
                z.add(el._id)
            else:
                e.append(el)
        data.models.elements = e
        for bl in data.models.beamlines:
            i = []
            for it in bl["items"]:
                if it not in z:
                    i.append(it)
            bl["items"] = i

    def __beam_from_madx(self, madx):
        """The MAD-X beam's distribution, its values as MAD-X has them (ex.
        an expression), None when MAD-X's is unset (a schema placeholder);
        the reference particle is self.beam and self.particle_energy

        Returns:
            PKDict: dispersion (dx, dpx, dy, dpy with respect to PT, those
            the beam has), dp_s_coupling, ex, ey [m], matched (the twiss is
            the periodic twiss), npart (more than 1), particle_count (the
            macro-particles), sige, sigt (c * sigma t [m]), twiss (alpha_x,
            beta_x, alpha_y, beta_y, those the beam has)
        """
        v = self._find_var(madx, "dp_s_coupling")
        n = self._val(self.beam.npart)
        res = PKDict(
            dispersion=self._beam_dispersion(madx),
            dp_s_coupling=v.value if v else None,
            matched=self._is_twiss_matched(madx),
            npart=n if n > 1 else None,
            particle_count=self._particle_count(madx),
            # sige's default is a real energy spread, see _is_beam_value_set()
            sige=self.beam.sige,
            twiss=self._beam_twiss(madx),
        )
        for f in ("ex", "ey", "sigt"):
            res[f] = self.beam[f] if self._is_beam_value_set(f) else None
        return res

    def __beam_to_madx(self, madx, beam):
        """Set the MAD-X beam from the code's `beam` (_beam_to_madx()):
        particle, mass [GeV], charge [e] and pc [GeV/c] the reference
        particle, when the code doesn't set it; distribution, see
        _madx_distribution(); dp_s_coupling, npart and particle_count (the
        macro-particles), each when not None; and twiss, MAD-X's twiss
        command's initial values, False for none (ex. periodic), by default
        the distribution's twiss when it has one, see initial_twiss()
        """
        d = beam.get("distribution")
        if beam.get("particle"):
            self._madx_beam(madx, beam.particle, beam.mass, beam.charge, beam.pc, d)
        elif d:
            self._madx_distribution(madx, d)
        if beam.get("dp_s_coupling") is not None:
            self._replace_var(madx, "dp_s_coupling", beam.dp_s_coupling)
        if beam.get("particle_count") is not None:
            self._set_particle_count(madx, beam.particle_count)
        if beam.get("npart") is not None:
            LatticeUtil.find_first_command(madx, "beam").npart = beam.npart
        t = beam.get("twiss")
        if t:
            initial_twiss(madx, t)
        elif t is None and d and all(f in d for f in self._BEAM_TWISS_VARS):
            initial_twiss(madx)

    def __copy_element(self, element):
        """`element` as the other code's, see _ELEMENTS

        Returns:
            PKDict: None when the element isn't copied, see _FROM_MADX
        """
        to_madx = self.to_class.sim_type() == "madx"
        if not to_madx and self._FROM_MADX.get(element.type, "") is None:
            return None
        c = element.type if to_madx else self._FROM_MADX.get(element.type)
        if c not in self._ELEMENTS:
            pkdlog("Unhandled element type: {}", element.type)
            c = self._FROM_MADX.DRIFT
            element.type = c if to_madx else "DRIFT"
            if "l" not in element:
                element.l = 0
        e = self._ELEMENTS[c]
        res = PKDict(name=element.name, type=e[0] if to_madx else c, _id=element._id)
        for f in e[1:]:
            f, m = f.split("=") if "=" in f else (f, f)
            s, d = (f, m) if to_madx else (m, f)
            if s in element:
                res[d] = element[s]
        self._fixup_element(element, res)
        h = getattr(
            self,
            f"_{'to' if to_madx else 'from'}_madx_{element.type.lower()}",
            None,
        )
        if h:
            h(element, res)
        self.to_class.update_model_defaults(res, res.type)
        return res

    def __init_direction(self, data, from_class, to_class):
        self.from_class = sirepo.sim_data.get_class(from_class)
        self.to_class = sirepo.sim_data.get_class(to_class)
        self.vars = sirepo.template.import_module(self.from_class.sim_type()).code_var(
            data.models.rpnVariables
        )

    def __is_builtin(self, variable):
        """Is `variable` one of MAD-X's (and OPAL's) predefined constants, ex.
        pi, which a code without them defines? Redefining one is an error
        in OPAL."""
        import sirepo.template.madx

        c = sirepo.template.madx.MADX_CONSTANTS.get(variable.name.lower())
        if c is None:
            return False
        try:
            return math.isclose(float(variable.value), c, rel_tol=1e-6)
        except (TypeError, ValueError):
            return False

    def __normalize_madx_beam(self, data):
        from sirepo.template import madx

        self.beam = copy.deepcopy(LatticeUtil.find_first_command(data, "beam"))
        cv = madx.code_var(data.models.rpnVariables)
        for f in ParticleEnergy.ENERGY_PRIORITY.madx:
            self.beam[f] = cv.eval_var_with_assert(self.beam[f])
        self.particle_energy = ParticleEnergy.compute_energy(
            self.from_class.sim_type(),
            self.beam.particle,
            self.beam.copy(),
        )
        self.beam.mass = ParticleEnergy.get_mass(
            self.from_class.sim_type(), self.beam.particle, self.beam
        )
        self.beam.charge = ParticleEnergy.get_charge(
            self.from_class.sim_type(), self.beam.particle, self.beam
        )
        beta_gamma = self.particle_energy.beta * self.particle_energy.gamma
        for dim in ("x", "y"):
            if (
                self.beam[f"e{dim}"]
                == self.from_class.schema().model.command_beam[f"e{dim}"][2]
                and self.beam[f"e{dim}n"]
            ):
                self.beam[f"e{dim}"] = self._val(self.beam[f"e{dim}n"]) / beta_gamma
        return data

    def _replace_var(self, data, name, value):
        v = self._find_var(data, name)
        if v:
            v.value = value
        else:
            data.models.rpnVariables.append(
                PKDict(
                    name=self._var_name(name),
                    value=value,
                )
            )

    def _rf_gap_gain(self, length, frequency):
        """On crest energy gain of a single gap Ez = sin^2(pi z / length)
        per its peak field, including the transit time at the beam's velocity

        Args:
            length (float): gap length [m]
            frequency (float): [Hz]
        Returns:
            float: [m], so [MV] per [MV/m]
        """
        z = numpy.linspace(0, length, 401)
        k = 2 * math.pi * frequency / (self.particle_energy.beta * scipy.constants.c)
        return abs(
            numpy.trapezoid(
                numpy.sin(math.pi * z / length) ** 2 * numpy.exp(1j * k * z), z
            )
        )

    def _scale(self, value, op, factor):
        """`value` times (op "*") or divided by (op "/") `factor`, a number
        as text; an expression stays an expression, undoing a scale the
        opposite conversion applied"""
        try:
            v = float(value)
        except (TypeError, ValueError):
            u = " {} {}".format("/" if op == "*" else "*", factor)
            if str(value).endswith(u):
                return value[: -len(u)]
            return f"{value} {op} {factor}"
        return v * float(factor) if op == "*" else v / float(factor)

    def _skew_as_tilt(self, element_in, element_out, order):
        """A MAD-X multipole's normal and skew strength (ex. k1 and k1s,
        order 1) as a normal strength rotated by tilt"""
        n = f"k{order}"
        k = self._val(element_in[n])
        ks = self._val(element_in[f"{n}s"])
        if ks:
            element_out[n] = math.hypot(k, ks)
            element_out.tilt = self._val(element_in.tilt) + math.atan2(ks, k) / (
                order + 1
            )

    def _slices(self, value, per_slice, minimum):
        """Slices of at most `per_slice` of `value` (ex. a bend's angle)

        Returns:
            int: None when not more than `minimum`
        """
        res = math.ceil(abs(value) / per_slice)
        return res if res > minimum else None

    def _thicken_thin_cavities(self, madx):
        """Give each zero length RFCAVITY of `madx` _THIN_CAVITY_LENGTH,
        for codes with field map cavities. It stays centered on its position
        by shortening the nearest drift on either side, past zero length
        elements, with new drift elements so other uses are unchanged. A
        cavity without those drifts in every beamline stays thin.

        Args:
            madx (PKDict): MAD-X data, modified
        """
        from sirepo.template import madx as madx_template

        cv = madx_template.code_var(madx.models.rpnVariables)
        elements = PKDict({e._id: e for e in madx.models.elements})
        remaining = PKDict()

        def _drift(beamline, index, step):
            items = beamline["items"]
            i = index + step
            while 0 <= i < len(items):
                e = elements.get(abs(items[i]))
                if e is None:
                    return None
                l = remaining.get(
                    (beamline.id, i), cv.eval_var_with_assert(e.get("l", 0))
                )
                if e.type == "DRIFT" and l >= half:
                    return i
                if l:
                    return None
                i += step
            return None

        half = self._THIN_CAVITY_LENGTH / 2
        for c in madx.models.elements:
            if c.type != "RFCAVITY" or cv.eval_var_with_assert(c.l):
                continue
            d = []
            for b in madx.models.beamlines:
                for i, item in enumerate(b["items"]):
                    if abs(item) == c._id:
                        d.extend((b, _drift(b, i, s)) for s in (-1, 1))
            if not d:
                continue
            if any(i is None for _, i in d):
                pkdlog(
                    "RFCAVITY={} has zero length and no drifts of {} m beside it, left thin",
                    c.name,
                    half,
                )
                continue
            for b, i in d:
                k = (b.id, i)
                remaining[k] = (
                    remaining.get(
                        k, cv.eval_var_with_assert(elements[abs(b["items"][i])].l)
                    )
                    - half
                )
            c.l = self._THIN_CAVITY_LENGTH
        names = set(e.name for e in madx.models.elements)
        drifts = PKDict()
        for b in madx.models.beamlines:
            for i, item in enumerate(b["items"]):
                if (b.id, i) not in remaining:
                    continue
                e = elements[abs(item)]
                k = (e._id, remaining[(b.id, i)])
                if k not in drifts:
                    n = 1
                    while f"{e.name}_{n}" in names:
                        n += 1
                    drifts[k] = copy.deepcopy(e).pkupdate(
                        _id=LatticeUtil.max_id(madx) + 1,
                        name=f"{e.name}_{n}",
                        l=k[1],
                    )
                    names.add(drifts[k].name)
                    madx.models.elements.append(drifts[k])
                b["items"][i] = drifts[k]._id

    def _val(self, var_value):
        """`var_value` evaluated with the source simulation's variables"""
        return self.vars.eval_var_with_assert(var_value)

    def _var_name(self, name):
        return f"sr_{name}"


def _converter(sim_type):
    if sim_type == "elegant":
        from sirepo.template.elegant import ElegantMadxConverter

        return ElegantMadxConverter(qcall=None)
    if sim_type == "opal":
        from sirepo.template.opal import OpalMadxConverter

        return OpalMadxConverter(qcall=None)
    if sim_type == "rftrack":
        from sirepo.template.rftrack import RftrackMadxConverter

        return RftrackMadxConverter(qcall=None)
    raise AssertionError(f"no MAD-X converter for sim_type={sim_type}")
