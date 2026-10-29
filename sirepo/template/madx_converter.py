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
import scipy.constants
import sirepo.sim_data
import sirepo.template

# The beam's values Sirepo's MAD-X export carries as variables, see
# beam_var(), madx._bunch_vars() and madx_parser._fixup_beam_vars()
#: the beam's dispersion at the start, with respect to PT
BEAM_DISPERSION_VARS = ("dpx", "dpy", "dx", "dy")
#: the beam's twiss at the start
BEAM_TWISS_VARS = ("alpha_x", "alpha_y", "beta_x", "beta_y")
#: 1 when the beam's twiss is the lattice's periodic twiss
MATCH_TWISS_VAR = "match_twiss_parameters"
#: the macro-particle count
PARTICLE_COUNT_VAR = "n_particles_per_bunch"


def beam_var(name):
    """The MAD-X variable which carries a beam value, ex. sr_beta_x

    Args:
        name (str): ex. beta_x, see BEAM_TWISS_VARS
    Returns:
        str: variable name
    """
    return "sr_" + name


def convert_lattice(data, to_sim_type):
    """Convert elegant, MAD-X, OPAL or RF-Track `data` to another of those
    codes, the same way as exporting a MAD-X lattice and importing it.

    Args:
        data (PKDict): simulationType and models of the source simulation
        to_sim_type (str): target code
    Returns:
        PKDict: the target simulation's data
    """
    import sirepo.feature_config
    import sirepo.template.madx

    f = data.simulationType
    # POSIT: _converter() has a converter for each LATTICE_CONVERSION_CODES
    # code but madx
    if (
        f == to_sim_type
        or f not in sirepo.feature_config.LATTICE_CONVERSION_CODES
        or to_sim_type not in sirepo.feature_config.LATTICE_CONVERSION_CODES
    ):
        raise AssertionError(f"invalid conversion from={f} to={to_sim_type}")
    if f == sirepo.template.madx.SIM_TYPE:
        t = sirepo.template.madx.python_source_for_model(data, model=None, qcall=None)
    elif to_sim_type == sirepo.template.madx.SIM_TYPE:
        res = _converter(f).to_madx(data)
    else:
        t = _converter(f).to_madx_text(data)
    if to_sim_type != sirepo.template.madx.SIM_TYPE:
        res = _converter(to_sim_type).from_madx_text(t)
    res.models.simulation.name = data.models.simulation.name
    return res


def has_initial_twiss(twiss):
    """Does a MAD-X twiss command (or ptc_twiss) have initial values, so
    describe a line? Without them it's periodic (a ring).

    Args:
        twiss (PKDict): the command, or None
    Returns:
        bool: betx and bety are set
    """
    return bool(
        twiss and all(twiss.get(f) not in (None, "", 0, "0") for f in ("betx", "bety"))
    )


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
    if not t or has_initial_twiss(t):
        return
    for d in ("x", "y"):
        for f, m in (("alpha", "alf"), ("beta", "bet")):
            t[f"{m}{d}"] = values[f"{f}_{d}"] if values else beam_var(f"{f}_{d}")
    n = set(v.name for v in madx.models.rpnVariables)
    for f in BEAM_DISPERSION_VARS:
        if values:
            if f in values:
                t[f] = values[f]
        elif beam_var(f) in n:
            t[f] = beam_var(f)


class MadxConverter:
    # Settings: each converter sets those it needs and MadxConverter reads
    # them, so a converter needn't use them itself.
    #: from_madx(): the code's own constants, see __fill_in_missing_constants()
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
    #: copied unchanged when the element has it, then the element type's
    #: handler, if any, does any other conversion (ex. units), see
    #: _element_handlers()
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
        self.__handlers = self._element_handlers()
        for d, t in (("from_madx", self._FROM_MADX), ("to_madx", self._ELEMENTS)):
            for k in self.__handlers[d]:
                if k not in t:
                    raise AssertionError(
                        f"{type(self).__name__} {d} handler type={k} not in its table"
                    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # __copy_element() makes an element type it doesn't know a drift
        if "DRIFT" not in cls._FROM_MADX:
            raise AssertionError(f"{cls.__name__} _FROM_MADX has no DRIFT")
        for k, v in cls._FROM_MADX.items():
            if v is None:
                # only DIPEDGE isn't copied: _merge_dipedges() removes it
                if k != "DIPEDGE" or not cls._DIPEDGE_BENDS:
                    raise AssertionError(
                        f"{cls.__name__} _FROM_MADX {k}=None without _DIPEDGE_BENDS"
                    )
            elif v not in cls._ELEMENTS:
                raise AssertionError(
                    f"{cls.__name__} _FROM_MADX {k}={v} not in _ELEMENTS"
                )

    def from_madx(self, data):
        """MAD-X `data` as the code's: the elements and beamlines, then the
        steps the class attributes select (_CONSTANTS, ...), the elements
        the handlers insert (_inserts), then _fixup_from_madx() with the
        beam, see __beam_from_madx()"""
        import sirepo.template.madx

        self.__init_direction(data, sirepo.template.madx.SIM_TYPE, self.sim_type)
        self._inserts = PKDict()
        self._init_from_madx(data)
        if self._THICKEN_THIN_CAVITIES:
            self._thicken_thin_cavities(data)
        res = self.__fill_in_missing_constants(
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
        import sirepo.template.madx

        self.__init_direction(data, self.sim_type, sirepo.template.madx.SIM_TYPE)
        self._inserts = PKDict()
        self._init_to_madx(data)
        res = self._convert(data)
        self._insert_elements(res, self._inserts)
        self.__beam_to_madx(res, self._beam_to_madx(data, res))
        self._fixup_to_madx(data, res)
        return res

    def to_madx_text(self, data):
        import sirepo.template.madx

        return sirepo.template.madx.python_source_for_model(
            self.to_madx(data),
            model=None,
            qcall=self.qcall,
        )

    def _add_inserts(self, element_id, before=None, after=None):
        """Elements to insert beside the converted element `element_id` in
        every beamline, by a handler during from_madx() or to_madx()

        Args:
            element_id (int): the converted element's _id
            before (list): new elements before it
            after (list): new elements after it
        """
        self._inserts[element_id] = PKDict(before=before or [], after=after or [])

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
        BEAM_DISPERSION_VARS

        Returns:
            PKDict: ex. dx=value
        """
        res = PKDict()
        for f in BEAM_DISPERSION_VARS:
            v = self._find_var(madx, f)
            if v:
                res[f] = v.value
        return res

    def _beam_for_madx(
        self,
        distribution=None,
        dp_s_coupling=None,
        initial_twiss=None,
        npart=None,
        particle_count=None,
        periodic_twiss=False,
        reference=None,
    ):
        """The code's beam for _beam_to_madx()

        Args:
            distribution (PKDict): see _madx_distribution()
            dp_s_coupling (float): z-pz correlation
            initial_twiss (PKDict): MAD-X's twiss command's initial values,
                see initial_twiss(); default the distribution's twiss
            npart (float): the bunch's particles
            particle_count (int): the macro-particles
            periodic_twiss (bool): MAD-X's twiss command stays periodic
            reference (PKDict): particle, mass [GeV], charge [e] and pc
                [GeV/c], when the code doesn't set MAD-X's beam itself
        Returns:
            PKDict: the beam
        """
        return PKDict(
            distribution=distribution,
            dp_s_coupling=dp_s_coupling,
            initial_twiss=initial_twiss,
            npart=npart,
            particle_count=particle_count,
            periodic_twiss=periodic_twiss,
            reference=reference,
        )

    def _beam_to_madx(self, data, madx):
        """The code's beam for to_madx(), see _beam_for_madx()

        Returns:
            PKDict: the beam, empty (_beam_for_madx()) without one
        """
        return self._beam_for_madx()

    def _beam_twiss(self, madx):
        """The beam's twiss variables present in `madx`, see
        BEAM_TWISS_VARS

        Returns:
            PKDict: ex. alpha_x=value
        """
        res = PKDict()
        for f in BEAM_TWISS_VARS:
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
            # a MAD-X type which isn't copied, see _FROM_MADX
            if not self.__is_to_madx and self._FROM_MADX.get(e.type, "") is None:
                continue
            self.result.models.elements.append(self.__copy_element(copy.deepcopy(e)))

    def _crest_offset(self, lag):
        """MAD-X RF `lag` [turns] as the phase offset from crest [turns],
        in [-0.5, 0.5)"""
        res = (self._val(lag) - self._MADX_CREST_LAG) % 1
        return res - 1 if res >= 0.5 else res

    def _element_handlers(self):
        """The element types' handlers: from_madx by MAD-X type, to_madx by
        the code's type, each called as handler(element_in, element_out)
        after the fields _ELEMENTS copies

        Returns:
            PKDict: from_madx and to_madx, type to handler
        """
        return PKDict(from_madx=PKDict(), to_madx=PKDict())

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

    def _fixup_to_madx(self, data, madx):
        """The code's own steps at the end of to_madx(), after the beam"""
        pass

    def _init_from_madx(self, madx):
        """The code's own state, before from_madx() converts `madx`"""
        pass

    def _init_to_madx(self, data):
        """The code's own state and changes to `data`, before to_madx()
        converts it"""
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
        # POSIT: a value equal to the schema's default wasn't given
        return (
            self._val(self.beam[field])
            != self.from_class.schema().model.command_beam[field][2]
        )

    def _is_twiss_matched(self, madx):
        """Is the beam's twiss the lattice's periodic twiss? see
        MATCH_TWISS_VAR"""
        v = self._find_var(madx, MATCH_TWISS_VAR)
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
        if not all(f in beam for f in BEAM_TWISS_VARS):
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
        for f in BEAM_DISPERSION_VARS:
            if f in beam:
                self._replace_var(madx, f, beam[f])
                madx.models.bunch[f] = self._val(beam[f])

    def _madx_particle(self, mass, charge):
        """MAD-X's named particle (not ion) with `mass` [GeV] and `charge`
        [e], ex. a code's custom antiproton, or "other"
        """
        for k, v in (
            sirepo.sim_data.get_class("madx").schema().constants.particleMassAndCharge
        ).items():
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
        """The macro-particle count variable's value, see PARTICLE_COUNT_VAR

        Returns:
            int: None if `madx` has none
        """
        v = self._find_var(madx, PARTICLE_COUNT_VAR)
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

    def _rf_gap_gain(self, length, frequency, beta):
        """On crest energy gain of a single gap Ez = sin^2(pi z / length)
        per its peak field, including the transit time at the beam's velocity

        Args:
            length (float): gap length [m]
            frequency (float): [Hz]
            beta (float): the beam's v / c
        Returns:
            float: [m], so [MV] per [MV/m]
        """
        z = numpy.linspace(0, length, 401)
        k = 2 * math.pi * frequency / (beta * scipy.constants.c)
        return abs(
            numpy.trapezoid(
                numpy.sin(math.pi * z / length) ** 2 * numpy.exp(1j * k * z), z
            )
        )

    def _set_particle_count(self, madx, count):
        """The macro-particle `count` as the variable and the MAD-X bunch's
        numberOfParticles, within its limits (to_madx)"""
        n = int(round(float(count)))
        self._replace_var(madx, PARTICLE_COUNT_VAR, n)
        s = self.to_class.schema().model.bunch.numberOfParticles
        madx.models.bunch.numberOfParticles = min(max(n, s[4]), s[5])
        if madx.models.bunch.numberOfParticles != n:
            pkdlog(
                "particle count={} limited to MAD-X's {}",
                n,
                madx.models.bunch.numberOfParticles,
            )

    def _thicken_thin_cavities(self, madx):
        """Give each zero length RFCAVITY of `madx` _THIN_CAVITY_LENGTH,
        for codes with field map cavities. It stays centered on its position
        by shortening the nearest drift on either side, past zero length
        elements, with new drift elements so other uses are unchanged. A
        cavity without those drifts in every beamline stays thin.

        Args:
            madx (PKDict): MAD-X data, modified
        """
        import sirepo.template.madx

        s = PKDict(
            cv=sirepo.template.madx.code_var(madx.models.rpnVariables),
            elements=PKDict({e._id: e for e in madx.models.elements}),
            # (beamline id, item index): what thin cavities leave of a drift
            remaining=PKDict(),
        )
        for c in madx.models.elements:
            if (
                c.type == "RFCAVITY"
                and not s.cv.eval_var_with_assert(c.l)
                and self.__thicken_cavity(madx, s, c)
            ):
                c.l = self._THIN_CAVITY_LENGTH
        self.__shorten_drifts(madx, s)

    def _val(self, var_value):
        """`var_value` evaluated with the source simulation's variables"""
        return self.vars.eval_var_with_assert(var_value)

    def _var_name(self, name):
        return beam_var(name)

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
        """Set the MAD-X beam from the code's, see _beam_for_madx()"""
        d = beam.distribution
        r = beam.reference
        if r:
            self._madx_beam(madx, r.particle, r.mass, r.charge, r.pc, d)
        elif d:
            self._madx_distribution(madx, d)
        if beam.dp_s_coupling is not None:
            self._replace_var(madx, "dp_s_coupling", beam.dp_s_coupling)
        if beam.particle_count is not None:
            self._set_particle_count(madx, beam.particle_count)
        if beam.npart is not None:
            LatticeUtil.find_first_command(madx, "beam").npart = beam.npart
        if beam.periodic_twiss:
            return
        if beam.initial_twiss:
            initial_twiss(madx, beam.initial_twiss)
        elif d and all(f in d for f in BEAM_TWISS_VARS):
            initial_twiss(madx)

    def __copy_element(self, element):
        """`element` as the other code's, see _ELEMENTS"""
        res = self.__copy_fields(element, self.__element_type(element))
        self._fixup_element(element, res)
        h = self.__handlers["to_madx" if self.__is_to_madx else "from_madx"].get(
            element.type
        )
        if h:
            h(element, res)
        self.to_class.update_model_defaults(res, res.type)
        return res

    def __copy_fields(self, element, code_type):
        """`element`'s fields _ELEMENTS copies, as the other code's element"""

        def _names(field):
            # (source, destination) field names
            c, m = field.split("=") if "=" in field else (field, field)
            return (c, m) if self.__is_to_madx else (m, c)

        res = PKDict(
            name=element.name,
            type=self._ELEMENTS[code_type][0] if self.__is_to_madx else code_type,
            _id=element._id,
        )
        for s, d in map(_names, self._ELEMENTS[code_type][1:]):
            if s in element:
                res[d] = element[s]
        return res

    def __drift_beside(self, state, beamline, index, step):
        """The index of the drift long enough for half a thin cavity at
        `index`, before (`step` -1) or after (1) it, past zero length
        elements, see _thicken_thin_cavities()

        Returns:
            int: -1 when there's none
        """
        i = index + step
        while 0 <= i < len(beamline["items"]):
            e = state.elements.get(abs(beamline["items"][i]))
            if e is None:
                return -1
            l = state.remaining.get(
                (beamline.id, i), state.cv.eval_var_with_assert(e.get("l", 0))
            )
            if e.type == "DRIFT" and l >= self._THIN_CAVITY_LENGTH / 2:
                return i
            if l:
                return -1
            i += step
        return -1

    def __element_type(self, element):
        """The code's type for `element`; one it doesn't convert becomes a
        drift"""
        res = element.type if self.__is_to_madx else self._FROM_MADX.get(element.type)
        if res in self._ELEMENTS:
            return res
        pkdlog("Unhandled element type: {}", element.type)
        res = self._FROM_MADX.DRIFT
        element.type = res if self.__is_to_madx else "DRIFT"
        if "l" not in element:
            element.l = 0
        return res

    def __fill_in_missing_constants(self, data, constants):
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

    def __init_direction(self, data, from_class, to_class):
        self.from_class = sirepo.sim_data.get_class(from_class)
        self.to_class = sirepo.sim_data.get_class(to_class)
        self.__is_to_madx = self.to_class.sim_type() == "madx"
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
        import sirepo.template.madx

        self.beam = copy.deepcopy(LatticeUtil.find_first_command(data, "beam"))
        cv = sirepo.template.madx.code_var(data.models.rpnVariables)
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
        for d in ("x", "y"):
            if sirepo.template.madx.uses_normalized_emittance(self.beam, d, cv):
                self.beam[f"e{d}"] = self._val(self.beam[f"e{d}n"]) / (
                    self.particle_energy.beta * self.particle_energy.gamma
                )
        return data

    def __shorten_drifts(self, madx, state):
        """Replace the drifts thin cavities shorten with new, shorter ones,
        see _thicken_thin_cavities()"""
        n = set(e.name for e in madx.models.elements)
        d = PKDict()
        for b in madx.models.beamlines:
            for i, item in enumerate(b["items"]):
                if (b.id, i) in state.remaining:
                    b["items"][i] = self.__shortened_drift(
                        madx,
                        d,
                        n,
                        state.elements[abs(item)],
                        state.remaining[(b.id, i)],
                    )._id

    def __shortened_drift(self, madx, drifts, names, drift, length):
        """`drift` at `length`, one new element for each drift and length

        Args:
            drifts (PKDict): (drift _id, length) to the new elements
            names (set): element names, the new one's added
        Returns:
            PKDict: the new element
        """
        k = (drift._id, length)
        if k not in drifts:
            n = 1
            while f"{drift.name}_{n}" in names:
                n += 1
            drifts[k] = copy.deepcopy(drift).pkupdate(
                _id=LatticeUtil.max_id(madx) + 1,
                name=f"{drift.name}_{n}",
                l=length,
            )
            names.add(drifts[k].name)
            madx.models.elements.append(drifts[k])
        return drifts[k]

    def __thicken_cavity(self, madx, state, cavity):
        """Shorten the drifts beside `cavity` in every beamline by half of
        _THIN_CAVITY_LENGTH, in state.remaining

        Returns:
            bool: every use of `cavity` has the drifts, so it is thickened
        """
        d = []
        for b in madx.models.beamlines:
            for i, item in enumerate(b["items"]):
                if abs(item) == cavity._id:
                    d.extend((b, self.__drift_beside(state, b, i, s)) for s in (-1, 1))
        if not d:
            return False
        if any(i < 0 for _, i in d):
            pkdlog(
                "RFCAVITY={} has zero length and no drifts of {} m beside it, left thin",
                cavity.name,
                self._THIN_CAVITY_LENGTH / 2,
            )
            return False
        for b, i in d:
            state.remaining[(b.id, i)] = (
                state.remaining.get(
                    (b.id, i),
                    state.cv.eval_var_with_assert(state.elements[abs(b["items"][i])].l),
                )
                - self._THIN_CAVITY_LENGTH / 2
            )
        return True


def _converter(sim_type):
    # POSIT: a converter for each feature_config.LATTICE_CONVERSION_CODES code
    # but madx
    if sim_type == "elegant":
        import sirepo.template.elegant

        return sirepo.template.elegant.ElegantMadxConverter(qcall=None)
    if sim_type == "opal":
        import sirepo.template.opal

        return sirepo.template.opal.OpalMadxConverter(qcall=None)
    if sim_type == "rftrack":
        import sirepo.template.rftrack

        return sirepo.template.rftrack.RftrackMadxConverter(qcall=None)
    raise AssertionError(f"no MAD-X converter for sim_type={sim_type}")
