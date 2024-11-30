"""elegant execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pmd_beamphysics import ParticleGroup
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from rsbeams.rsdata.SDDS import writeSDDS
from rsbeams.rsstats import kinematic
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import elegant_command_importer
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_importer
from sirepo.template import lattice
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
from sirepo.template.madx_converter import MadxConverter
import copy
import glob
import h5py
import math
import numpy
import os.path
import pmd_beamphysics.readers
import pygments
import pygments.formatters
import pygments.lexers
import re
import scipy.constants
import sirepo.lib
import sirepo.sim_data
import stat


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

ELEGANT_LOG_FILE = "elegant.log"

WANT_BROWSER_FRAME_CACHE = True

_ERROR_RE = re.compile(
    r"^warn|^error|wrong units|^fatal |no expansion for entity|unable to|warning\:|^0 particles left|^unknown token|^terminated by sig|no such file or directory|no parameter name found|Problem opening |Terminated by SIG|No filename given|^MPI_ERR",
    re.IGNORECASE,
)

_ERROR_IGNORE_RE = re.compile(
    r"^warn.* does not have a parameter",
    re.IGNORECASE,
)

_ELEGANT_CONSTANTS = PKDict(
    pi=3.141592653589793,
    c_cgs=2.99792458e10,
    c_mks=2.99792458e8,
    e_cgs=4.80325e-10,
    e_mks=1.60217733e-19,
    me_cgs=9.1093897e-28,
    me_mks=9.1093897e-31,
    re_cgs=2.81794092e-13,
    re_mks=2.81794092e-15,
    kb_cgs=1.380658e-16,
    kb_mks=1.380658e-23,
    mev=0.51099906,
    hbar_mks=1.0545887e-34,
    hbar_MeVs=6.582173e-22,
    mp_mks=1.6726485e-27,
    mu_o=1.25663706143592e-06,
    eps_o=8.85418781762039e-12,
)

_ELEGANT_SEMAPHORE_FILE = "run_setup.semaphore"

_MPI_IO_WRITE_BUFFER_SIZE = "1048576"

_FIELD_LABEL = PKDict(
    x="x [m]",
    xp="x' [rad]",
    y="y [m]",
    yp="y' [rad]",
    t="t [s]",
    p="p (mₑc)",
    s="s [m]",
    LinearDensity="Linear Density (C/s)",
    LinearDensityDeriv="LinearDensityDeriv (C/s²)",
    GammaDeriv="GammaDeriv (1/m)",
)

_MULTIFILE_SUFFIX = "-%03ld"

_OUTPUT_INFO_FILE = "outputInfo.json"

_OUTPUT_INFO_VERSION = "3"

_PLOT_TITLE = PKDict(
    {
        "x-xp": "Horizontal",
        "y-yp": "Vertical",
        "x-y": "Cross-section",
        "t-p": "Longitudinal",
    }
)

_SDDS_INDEX = None

_SIMPLE_UNITS = ["m", "s", "C", "rad", "eV"]

_X_FIELD = "s"


class CommandIterator(lattice.ElementIterator):
    def start(self, model):
        super(CommandIterator, self).start(model)
        if model._type == "run_setup":
            self.fields.append(["semaphore_file", _ELEGANT_SEMAPHORE_FILE])
        elif model._type == "global_settings":
            self.fields.append(["mpi_io_write_buffer_size", _MPI_IO_WRITE_BUFFER_SIZE])


class LibAdapter(sirepo.lib.LibAdapterBase):
    def parse_file(self, path):
        def _input_files(model_type):
            return [
                k for k, v in SCHEMA.model[model_type].items() if "InputFile" in v[1]
            ]

        def _verify_files(model, model_type):
            self._verify_files(
                path,
                [
                    model[x]
                    for x in filter(
                        lambda f: model[f],
                        _input_files(model_type),
                    )
                ],
            )

        d = parse_input_text(path, update_filenames=False)
        r = self._run_setup(d)
        l = r.lattice
        d = parse_input_text(
            self._lattice_path(path.dirpath(), d),
            input_data=d,
            update_filenames=False,
        )
        for i in d.models.elements:
            _verify_files(i, i.type)
        for i in d.models.commands:
            _verify_files(i, lattice.LatticeUtil.model_name_for_data(i))
        r.lattice = l
        return self._convert(d)

    def write_files(self, data, source_path, dest_dir):
        """writes files for the simulation

        Returns:
            PKDict: structure of files written (debugging only)
        """

        def _unescape(value):
            return re.sub(r"\\\\", r"\\", value)

        class _G(_Generate):
            def _abspath(self, basename):
                return source_path.new(basename=basename)

            def _input_file(self, model_name, field, filename):
                return filename

            def _lattice_filename(self, value):
                return value

        g = _G(data, update_output_filenames=False)
        g.sim()
        v = g.jinja_env
        r = PKDict(
            commands=dest_dir.join(source_path.basename),
            lattice=self._lattice_path(dest_dir, data),
        )
        pkio.write_text(r.commands, _unescape(v.commands))
        if not r.lattice.exists():
            pkio.write_text(r.lattice, v.rpn_variables + v.lattice)
        self._write_input_files(data, source_path, dest_dir)
        f = g.filename_map
        r.output_files = [f[k] for k in f.keys_in_order]
        return r

    def _lattice_path(self, dest_dir, data):
        return dest_dir.join(self._run_setup(data).lattice)

    def _run_setup(self, data):
        return LatticeUtil.find_first_command(data, "run_setup")


class OutputFileIterator(lattice.ModelIterator):
    def __init__(self, update_filenames):
        self.result = PKDict(
            keys_in_order=[],
        )
        self.model_index = PKDict()
        self._update_filenames = update_filenames

    def field(self, model, field_schema, field):
        if field == lattice.ElementIterator.IS_DISABLED_FIELD or field == "_super":
            return
        self.field_index += 1
        if field_schema[1] in ("OutputFile", "MultiOutputFile") and model[field]:
            if self._update_filenames:
                multi_suffix = (
                    _MULTIFILE_SUFFIX if field_schema[1] == "MultiOutputFile" else ""
                )
                if LatticeUtil.is_command(model):
                    suffix = self._command_file_extension(model)
                    filename = "{}{}.{}.{}{}".format(
                        model._type,
                        (
                            self.model_index[self.model_name]
                            if self.model_index[self.model_name] > 1
                            else ""
                        ),
                        field,
                        multi_suffix,
                        suffix,
                    )
                else:
                    filename = "{}.{}{}.sdds".format(
                        model.name,
                        field,
                        multi_suffix,
                    )
            else:
                filename = model[field]
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

    def _command_file_extension(self, model):
        if model._type == "save_lattice":
            return "lte"
        if model._type == "global_settings":
            return "txt"
        return "sdds"


class ElegantMadxConverter(MadxConverter):
    _BEAM_VARS = [
        "beta_x",
        "beta_y",
        "alpha_x",
        "alpha_y",
        "n_particles_per_bunch",
        "dp_s_coupling",
    ]
    _PARTICLE_MAP = PKDict(
        electron="electron",
        positron="positron",
        proton="proton",
        muon="negmuon",
        negmuon="muon",
        custom="other",
    )
    _FIELD_MAP = [
        [
            "DRIFT",
            ["DRIF", "l"],
            ["CSRDRIFT", "l"],
            ["EDRIFT", "l"],
            ["LSCDRIFT", "l"],
        ],
        [
            "SBEND",
            [
                "CSBEND",
                "l",
                "angle",
                "k1",
                "k2",
                "e1",
                "e2",
                "h1",
                "h2",
                "tilt",
                "hgap",
                "fint",
            ],
            [
                "SBEN",
                "l",
                "angle",
                "k1",
                "k2",
                "e1",
                "e2",
                "h1",
                "h2",
                "tilt",
                "hgap",
                "fint",
            ],
            [
                "CSRCSBEND",
                "l",
                "angle",
                "k1",
                "k2",
                "e1",
                "e2",
                "h1",
                "h2",
                "tilt",
                "hgap",
                "fint",
            ],
            [
                "KSBEND",
                "l",
                "angle",
                "k1",
                "k2",
                "e1",
                "e2",
                "h1",
                "h2",
                "tilt",
                "hgap",
                "fint",
            ],
            ["NIBEND", "l", "angle", "e1", "e2", "tilt", "hgap", "fint"],
        ],
        [
            "RBEND",
            [
                "RBEN",
                "l",
                "angle",
                "k1",
                "k2",
                "e1",
                "e2",
                "h1",
                "h2",
                "tilt",
                "hgap",
                "fint",
            ],
            ["TUBEND", "l", "angle"],
        ],
        [
            # DIPEDGE attributes will be combined with any CSBEND or RBEN elements nearby
            "DIPEDGE",
            ["CSBEND", "e1", "tilt", "hgap", "fint"],
        ],
        [
            "QUADRUPOLE",
            ["QUAD", "l", "k1", "tilt"],
            ["KQUAD", "l", "k1", "tilt"],
        ],
        [
            "SEXTUPOLE",
            ["SEXT", "l", "k2", "tilt"],
            ["KSEXT", "l", "k2", "tilt"],
        ],
        [
            "OCTUPOLE",
            ["OCTU", "l", "k3", "tilt"],
            ["KOCT", "l", "k3", "tilt"],
        ],
        [
            "SOLENOID",
            ["SOLE", "l", "ks"],
        ],
        [
            "MULTIPOLE",
            # TODO(pjm): compute knl and order from first knl value in madx
            ["MULT", "tilt"],
        ],
        [
            "HKICKER",
            ["HKICK", "l", "kick", "tilt"],
            ["EHKICK", "l", "kick", "tilt"],
        ],
        [
            "VKICKER",
            ["VKICK", "l", "kick", "tilt"],
            ["EVKICK", "l", "kick", "tilt"],
        ],
        [
            "KICKER",
            ["KICKER", "l", "hkick", "vkick", "tilt"],
            ["EKICKER", "l", "hkick", "vkick", "tilt"],
        ],
        [
            "MARKER",
            ["MARK"],
        ],
        [
            "PLACEHOLDER",
            ["DRIF", "l"],
        ],
        [
            "INSTRUMENT",
            ["DRIF", "l"],
        ],
        [
            "ECOLLIMATOR",
            ["ECOL", "l", "x_max=xsize", "y_max=ysize"],
        ],
        [
            "RCOLLIMATOR",
            ["RCOL", "l", "x_max=xsize", "y_max=ysize"],
        ],
        [
            "COLLIMATOR",
            ["ECOL", "l"],
        ],
        [
            "RFCAVITY",
            ["RFCA", "l", "volt", "freq", "phase=lag"],
            ["MODRF", "l", "volt", "freq", "phase=lag"],
            ["RAMPRF", "l", "volt", "freq", "phase=lag"],
            ["RFCW", "l", "volt", "freq", "phase=lag"],
        ],
        [
            "TWCAVITY",
            ["RFDF", "l", "voltage=volt", "frequency=freq", "phase=lag"],
        ],
        [
            "HMONITOR",
            ["HMON", "l"],
        ],
        [
            "VMONITOR",
            ["VMON", "l"],
        ],
        [
            "MONITOR",
            ["MONI", "l"],
            ["WATCH"],
        ],
        [
            "SROTATION",
            ["ROTATE", "tilt=angle"],
        ],
    ]
    _FIELD_SCALE = PKDict(
        RFCAVITY=PKDict(
            freq="1e6",
            volt="1e6",
        ),
        TWCAVITY=PKDict(
            freq="1e6",
            volt="1e6",
        ),
    )

    def __init__(self, qcall=None, **kwargs):
        super().__init__(
            SIM_TYPE,
            self._FIELD_MAP,
            downcase_variables=True,
            qcall=qcall,
            **kwargs,
        )

    def from_madx(self, madx):
        data = self.fill_in_missing_constants(
            super().from_madx(madx), _ELEGANT_CONSTANTS
        )
        self.__combine_dipedge(data)
        eb = LatticeUtil.find_first_command(data, "bunched_beam")
        mb = self.beam
        for f in self._BEAM_VARS:
            v = self._find_var(madx, f)
            if v:
                eb[f] = v.value
        ers = LatticeUtil.find_first_command(data, "run_setup")
        ers.p_central_mev = self.particle_energy.pc * 1e3
        eb.emit_x = mb.ex
        eb.emit_y = mb.ey
        eb.sigma_s = mb.sigt
        eb.sigma_dp = mb.sige

        if mb.particle != "electron":
            data.models.commands.insert(
                0,
                PKDict(
                    _id=LatticeUtil.max_id(data),
                    _type="change_particle",
                    name=self._PARTICLE_MAP.get(mb.particle, "custom"),
                    # TODO(pjm): custom particle should set mass_ratio and charge_ratio
                ),
            )
        return data

    def to_madx(self, data):
        madx = super().to_madx(data)
        eb = LatticeUtil.find_first_command(data, "bunched_beam")
        if not eb:
            return madx
        self.__normalize_elegant_beam(data, eb)
        mb = LatticeUtil.find_first_command(madx, "beam")
        particle = LatticeUtil.find_first_command(data, "change_particle")
        if particle:
            mb.particle = self._PARTICLE_MAP.get(particle.name, "other")
            # TODO(pjm): other particle should set mass and charge
        else:
            mb.particle = "electron"
        mb.energy = 0
        madx.models.bunch.beamDefinition = "pc"
        madx.models.bunch.longitudinalMethod = "2"
        mb.pc = eb.p_central_mev * 1e-3
        mb.sigt = eb.sigma_s
        mb.sige = eb.sigma_dp
        for f in self._BEAM_VARS:
            self._replace_var(madx, f, eb[f])
        for dim in ("x", "y"):
            mb[f"e{dim}"] = eb[f"emit_{dim}"]
            self._replace_var(
                madx,
                f"gamma_{dim}",
                "(1 + {} * {}) / {}".format(
                    self._var_name(f"alpha_{dim}"),
                    self._var_name(f"alpha_{dim}"),
                    self._var_name(f"beta_{dim}"),
                ),
            )
        return madx

    def _fixup_element(self, element_in, element_out):
        super()._fixup_element(element_in, element_out)
        if self.from_class.sim_type() == SIM_TYPE:
            el = element_out
            op = "/"
        else:
            el = element_in
            op = "*"
        scale = self._FIELD_SCALE.get(el.type)
        if scale:
            for f in scale:
                if f in element_out:
                    element_out[f] = f"{element_out[f]} {op} {scale[f]}"
        if element_in.type == "COLLIMATOR":
            m = re.search(r"^\{?\s*(.*?),\s*(.*?)\s*\}?$", element_in.aperture)
            if m:
                element_out.x_max = self.__val(m.group(1))
                element_out.y_max = self.__val(m.group(2))
            if element_in.apertype == "rectangle":
                element_out.type = "RCOL"
        elif element_in.type == "RFCAVITY":
            element_out.phase = self.__val(element_out.phase) * 360 + 180
            while element_out.phase >= 360:
                element_out.phase -= 360

    def __combine_dipedge(self, data):
        # DIPEDGE elements get converted into a CSBEND with no length
        # combine attributes with nearby CSBEND elements
        dmap = PKDict()
        bmap = PKDict()
        els = []
        for el in data.models.elements:
            if el.type == "CSBEND" or el.type == "RBEN":
                if el.l == 0:
                    dmap[el._id] = el
                    continue
                else:
                    bmap[el._id] = el
            els.append(el)
        data.models.elements = els
        for bl in data.models.beamlines:
            bl2 = []
            for i, id in enumerate(bl["items"]):
                if id in dmap:
                    if i > 0 and bl["items"][i - 1] in bmap:
                        # trailing dipedge
                        b = bmap[bl["items"][i - 1]]
                        d = dmap[id]
                        b.e2 = d.e1
                        b.fint2 = d.fint
                        b.hgap = d.hgap
                    continue
                if id in bmap and i > 0 and bl["items"][i - 1] in dmap:
                    # leading dipedge
                    d = dmap[bl["items"][i - 1]]
                    b = bmap[id]
                    b.e1 = d.e1
                    b.fint1 = d.fint
                    b.hgap = d.hgap
                    b.tilt = d.tilt
                bl2.append(id)
            bl["items"] = bl2

    def __normalize_elegant_beam(self, data, beam):
        # ensure p_central_mev, emit_x, emit_y, sigma_s, sigma_dp and dp_s_coupling are set
        # convert from other values if missing
        def _var(v):
            return self.vars.eval_var_with_assert(v)

        ers = LatticeUtil.find_first_command(data, "run_setup")
        if not ers:
            return
        if not _var(ers.p_central_mev):
            # TODO(pjm): use particle mass, don't assume electron
            ers.p_central_mev = _var(ers.p_central) * SCHEMA.constants.ELEGANT_ME_EV
        beam.p_central_mev = _var(ers.p_central_mev)
        beta_gamma = beam.p_central_mev / SCHEMA.constants.ELEGANT_ME_EV
        for f in ("x", "y"):
            emit = _var(beam[f"emit_{f}"])
            if not emit:
                # convert from normalized emittance
                emit = beam[f"emit_{f}"] = _var(beam[f"emit_n{f}"]) / beta_gamma
        if str(data.models.bunch.longitudinalMethod) == "2":
            # convert alpha_z --> dp_s_coupling
            beam.dp_s_coupling = -_var(beam.alpha_z) / math.sqrt(
                1 + pow(_var(beam.alpha_z), 2)
            )
        elif str(data.models.bunch.longitudinalMethod) == "3":
            # convert emit_z, beta_z, alpha_z --> sigma_s, sigma_dp, dp_s_coupling
            beam.sigma_s = math.sqrt(_var(beam.emit_z) * _var(beam.beta_z))
            gamma_z = (1 + _var(beam.alpha_z) ** 2) / _var(beam.beta_z)
            beam.sigma_dp = math.sqrt(_var(beam.emit_z) * gamma_z)
            beam.dp_s_coupling = -_var(beam.alpha_z) / math.sqrt(
                1 + pow(_var(beam.alpha_z), 2)
            )
        if _var(beam.momentum_chirp):
            beam.sigma_dp = math.sqrt(
                _var(beam.sigma_dp) ** 2
                + (_var(beam.sigma_s) * _var(beam.momentum_chirp)) ** 2
            )
            # TODO(pjm): determine conversion from momentum_chirp to db_s_coupling

    def __val(self, var_value):
        return self.vars.eval_var_with_assert(var_value)


def background_percent_complete(report, run_dir, is_running):
    def _percent(data, last_element, step):
        def _walk(beamline, index, elements, beamlines, beamline_map):
            # walk beamline in order, adding (<name>#<count> => index) to beamline_map
            for id in beamline["items"]:
                if id in elements:
                    name = elements[id].name
                    if name not in beamline_map:
                        beamline_map[name] = 0
                    beamline_map[name] += 1
                    beamline_map["{}#{}".format(name.upper(), beamline_map[name])] = (
                        index
                    )
                    index += 1
                else:
                    index = _walk(
                        beamlines[abs(id)], index, elements, beamlines, beamline_map
                    )
            return index

        if step > 1:
            cmd = LatticeUtil.find_first_command(data, "run_control")
            if cmd and cmd.n_steps:
                n_steps = 0
                if code_variable.CodeVar.is_var_value(cmd.n_steps):
                    n_steps = code_var(data.models.rpnVariables).eval_var(cmd.n_steps)[
                        0
                    ]
                else:
                    n_steps = int(cmd.n_steps)
                if n_steps and n_steps > 0:
                    return min(100, step * 100 / n_steps)
        if not last_element:
            return 0
        elements = PKDict()
        for e in data.models.elements:
            elements[e._id] = e
        beamlines = PKDict()
        for b in data.models.beamlines:
            beamlines[b.id] = b
        i = data.models.simulation.visualizationBeamlineId
        beamline_map = PKDict()
        count = _walk(beamlines[i], 1, elements, beamlines, beamline_map)
        index = beamline_map[last_element] if last_element in beamline_map else 0
        return min(100, index * 100 / count)

    # TODO(robnagler) remove duplication in run_dir.exists() (outer level?)
    alert, last_element, step = _parse_elegant_log(run_dir)
    res = PKDict(
        percentComplete=100,
        frameCount=0,
        alert=alert,
    )
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res.percentComplete = _percent(data, last_element, step)
        return res
    if not run_dir.join(_ELEGANT_SEMAPHORE_FILE).exists():
        return res
    output_info = _output_info(run_dir)
    return res.pkupdate(
        frameCount=1,
        outputInfo=output_info,
        lastUpdateTime=output_info[0].lastUpdateTime,
    )


def code_var(variables):
    return elegant_lattice_importer.elegant_code_var(variables)


def convert_to_sdds(openpmd_file):
    try:
        # use openPMD beamphysics format first
        pmd_beamphysics.interfaces.elegant.write_elegant(
            ParticleGroup(openpmd_file),
            openpmd_file + ".sdds",
        )
        return
    except KeyError:
        pass

    # manually convert from x,y,t format
    with h5py.File(openpmd_file, "r") as f:
        pp = pmd_beamphysics.readers.particle_paths(f)
        d = f[pp[-1]]
        if "beam" in d:
            d = d["beam"]
        elegant_t = -numpy.array(d["position/t"]) / scipy.constants.c
        ref = kinematic.Converter(
            mass=d.attrs["mass_ref"],
            mass_unit="SI",
            gamma=d.attrs["gamma_ref"],
        )(silent=True)
        elegant_p = kinematic.Converter(
            mass=d.attrs["mass_ref"],
            mass_unit="SI",
            gamma=numpy.array(d["momentum/t"]) * ref["betagamma"] + ref["gamma"],
        )(silent=True)["betagamma"]

        s = writeSDDS()
        s.create_column("x", numpy.array(d["position/x"]), "double", colUnits="m")
        s.create_column("xp", numpy.array(d["momentum/x"]), "double", colUnits="")
        s.create_column("y", numpy.array(d["position/y"]), "double", colUnits="m")
        s.create_column("yp", numpy.array(d["momentum/y"]), "double", colUnits="")
        s.create_column("t", elegant_t, "double", colUnits="s")
        s.create_column("p", elegant_p, "double", colUnits="m$be$nc")
        s.create_parameter("particles", elegant_p.size, "long")
        s.create_parameter("pCentral", ref["betagamma"], "double", parUnits="MeV/c")
        s.save_sdds(openpmd_file + ".sdds", dataMode="binary")


def extract_report_data(filename, frame_args, page_count=0):
    def _label(plot, sdds_units):
        if plot.label in _FIELD_LABEL:
            plot.label = _FIELD_LABEL[plot.label]
            return
        if sdds_units in _SIMPLE_UNITS:
            plot.label = "{} [{}]".format(plot.label, sdds_units)
            return
        plot.label = plot.label
        return

    def _title(xfield, yfield, page_index, page_count, position):
        title_key = xfield + "-" + yfield
        if title_key in _PLOT_TITLE:
            title = _PLOT_TITLE[title_key]
        else:
            title = "{} / {}".format(xfield, yfield)
        if position is not None:
            title += ", {0:.4g} m".format(position)
        if page_count > 1:
            title += ", Plot {} of {}".format(page_index + 1, page_count)
        return title

    x_field = "x" if "x" in frame_args else _X_FIELD
    plot_attrs = PKDict(
        format_plot=_label,
        page_index=frame_args.frameIndex,
        model=template_common.model_from_frame_args(frame_args),
        x_field=x_field,
    )
    _sdds_init()

    position = None
    if _is_multifile(filename):
        filename = filename % (frame_args.frameIndex + 1)
        if pkio.py_path(filename).exists():
            position = sdds_util.read_sdds_parameter(filename, "s")
        else:
            # for old sim output, use non-numbered file
            filename = re.sub("\-\d+\.sdds", ".sdds", filename)
    if not _is_histogram_file(
        filename,
        sdds_util.extract_sdds_column(filename, frame_args[x_field], 0)["column_names"],
    ):
        if page_count > 1:
            plot_attrs.pkupdate(
                title="Plot {} of {}".format(plot_attrs.page_index + 1, page_count)
            )

        return sdds_util.SDDSUtil(filename).lineplot(plot_attrs=plot_attrs)

    y_field = "y1" if "y1" in frame_args else "y"
    return sdds_util.SDDSUtil(filename).heatmap(
        plot_attrs=plot_attrs.pkupdate(
            title=_title(
                frame_args[x_field],
                frame_args[y_field],
                plot_attrs.page_index,
                page_count,
                position,
            ),
            y_field=y_field,
        )
    )


def generate_parameters_file(data, is_parallel=False, qcall=None):
    if "bunchReport" in data.get("report", ""):
        _prepare_bunch_simulation(data)
    return _Generate(data, qcall=qcall).sim(full=is_parallel)


def generate_variables(data):
    """Called by other templates"""

    def _gen(name, variables, visited):
        if name in visited:
            return ""
        visited[name] = True
        return f"% {_format_rpn_value(variables[name])} sto {name}\n"

    return code_var(data.models.rpnVariables).generate_variables(_gen, postfix=True)


def get_data_file(run_dir, model, frame, options):
    def _sdds(filename):
        if _is_multifile(filename):
            filename = filename % (frame + 1)
        path = run_dir.join(filename)
        if not path.check(file=True, exists=True):
            raise AssertionError(f"not found path={path}")
        if not options.suffix:
            return path
        if options.suffix != "csv":
            raise AssertionError(
                f"invalid suffix={options.suffix} for download path={path}"
            )
        out = elegant_common.subprocess_output(
            [
                "sddsprintout",
                "-noTitle",
                "-columns",
                "-spreadsheet=delimiter=\\,",
                "-formatDefaults=float=%1.8e,double=%1.16e,long=%1ld,short=%1hd",
                str(path),
            ],
        )
        if not out:
            raise AssertionError(
                f"invalid or empty output from sddsprintout path={path}"
            )
        return template_common.JobCmdFile(
            reply_uri=path.purebasename + ".csv",
            reply_content=out,
        )

    if frame >= 0:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        # ex. elementAnimation17-55
        i = LatticeUtil.file_id_from_output_model_name(model)
        return _sdds(_get_filename_for_element_id(i, data))
    if model == "animation":
        return template_common.text_data_file(ELEGANT_LOG_FILE, run_dir)
    return _sdds(_report_output_filename("bunchReport"))


def parse_input_text(
    path, text=None, input_data=None, update_filenames=True, qcall=None
):
    def _map(data):
        for cmd in data.models.commands:
            if cmd._type == "run_setup":
                cmd.lattice = "Lattice"
                break
        for cmd in data.models.commands:
            if cmd._type == "run_setup":
                name = cmd.use_beamline.upper()
                for bl in data.models.beamlines:
                    if bl.name.upper() == name:
                        cmd.use_beamline = bl.id
                        break

    if text is None:
        text = pkio.read_text(path)
    e = path.ext.lower()
    if e == ".ele":
        return elegant_command_importer.import_file(text, update_filenames)
    if e == ".lte":
        data = elegant_lattice_importer.import_file(text, input_data, update_filenames)
        if input_data:
            _map(data)
        return data
    if e == ".madx" or e == ".seq":
        return ElegantMadxConverter(qcall=qcall).from_madx_text(text)
    if e == ".in":
        from sirepo.template import opal_parser
        from sirepo.template.opal import OpalMadxConverter

        return ElegantMadxConverter(qcall=qcall).from_madx_text(
            OpalMadxConverter(qcall=qcall).to_madx_text(opal_parser.parse_file(text)[0])
        )
    raise IOError(
        f"{path.basename}: invalid file format; expecting .madx, .ele, .in or .lte"
    )


def parse_elegant_log(run_dir):
    # used by omega
    return _parse_elegant_log(run_dir)[0]


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def post_execution_processing(success_exit, run_dir, **kwargs):
    if success_exit:
        return None
    return _parse_elegant_log(run_dir)[0]


def prepare_sequential_output_file(run_dir, data):
    if data.report == "twissReport" or "bunchReport" in data.report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            output_file = run_dir.join(_report_output_filename(data.report))
            if output_file.exists():
                save_sequential_report_data(data, run_dir)


def python_source_for_model(data, model, qcall, **kwargs):
    if model == "madx":
        return ElegantMadxConverter(qcall=qcall).to_madx_text(data)
    return (
        generate_parameters_file(data, is_parallel=True, qcall=qcall)
        + """
with open('elegant.lte', 'w') as f:
    f.write(lattice_file)

with open('elegant.ele', 'w') as f:
    f.write(elegant_file)

import os
os.system('elegant elegant.ele')
"""
    )


def remove_last_frame(run_dir):
    pass


def save_sequential_report_data(data, run_dir):
    a = copy.deepcopy(data.models[data.report])
    a.frameReport = data.report
    if a.frameReport == "twissReport":
        a.x = "s"
        a.y = a.y1
    a.frameIndex = 0
    # extract_report_data() is expecting something that looks like frameArgs
    a.sim_in = PKDict(
        models=PKDict(
            {
                data.report: a,
            }
        )
    )
    template_common.write_sequential_result(
        extract_report_data(
            str(run_dir.join(_report_output_filename(a.frameReport))), a
        ),
        run_dir=run_dir,
    )


def sim_frame(frame_args):
    def _id(file_id, model_data, run_dir):
        return str(run_dir.join(_get_filename_for_element_id(file_id, model_data)))

    r = frame_args.frameReport
    page_count = 0
    for info in _output_info(frame_args.run_dir):
        if info.modelKey == r:
            page_count = info.pageCount
            frame_args.fieldRange = info.fieldRange
    frame_args.y = frame_args.y1
    return extract_report_data(
        _id(
            frame_args.xFileId,
            frame_args.sim_in,
            frame_args.run_dir,
        ),
        frame_args,
        page_count=page_count,
    )


def stateful_compute_get_beam_input_type(data, **kwargs):
    if data.args.input_file:
        data.input_type = _sdds_beam_type_from_file(
            _SIM_DATA.lib_file_abspath(data.args.input_file),
        )
    return data


def elegant_file_import(data):
    d = data.args.pkunchecked_nested_get("import_file_arguments")
    if d:
        d = pkjson.load_any(d)
    res = parse_input_text(
        path=pkio.py_path(data.args.basename),
        text=data.args.file_as_str,
        input_data=d,
    )
    if not d:
        res.models.simulation.name = data.args.purebasename
    r = LatticeUtil.find_first_command(res, "run_setup")
    if r and r.lattice != "Lattice":
        return PKDict(importState="needLattice", eleData=res, latticeFileName=r.lattice)
    return PKDict(imported_data=res)


def stateful_compute_import_file(data, **kwargs):
    return elegant_file_import(data)


def validate_file(file_type, path):
    err = None
    if file_type == "bunchFile-sourceFile":
        if _is_openpmd_file(path):
            # TODO(pjm): validate openPMD file
            pass
        else:
            _sdds_init()
            err = "expecting sdds file with (x, xp, y, yp, t, p) or (r, pr, pz, t, pphi) columns"
            if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(path)) == 1:
                beam_type = _sdds_beam_type(sdds.sddsdata.GetColumnNames(_SDDS_INDEX))
                if beam_type in ("elegant", "spiffe"):
                    sdds.sddsdata.ReadPage(_SDDS_INDEX)
                    if len(sdds.sddsdata.GetColumn(_SDDS_INDEX, 0)) > 0:
                        err = None
                    else:
                        err = "sdds file contains no rows"
            sdds.sddsdata.Terminate(_SDDS_INDEX)
    return err


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            is_parallel,
        ),
    )
    for b in _SIM_DATA.lib_file_basenames(data):
        if not b.startswith("SCRIPT-commandFile"):
            continue
        f = run_dir.join(b)
        if f.check(link=True):
            x = f.read_binary()
            f.remove()
            f.write_binary(x)
        f.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


class _Generate(sirepo.lib.GenerateBase):
    def __init__(self, data, validate=True, update_output_filenames=True, qcall=None):
        self.data = data
        self.qcall = qcall
        self._filename_map = None
        self._schema = SCHEMA
        self._update_output_filenames = update_output_filenames
        self._cv = code_var(data.models.rpnVariables)
        self._openpmd_files = []
        if validate:
            self._validate_data()

    @property
    def filename_map(self):
        if not self._filename_map:
            self._filename_map = _build_filename_map_from_util(
                self.util,
                self._update_output_filenames,
            )
        return self._filename_map

    def lattice_only(self):
        return self._lattice()

    def sim(self, full=True):
        d = self.data
        r, v = template_common.generate_parameters_file(d)
        v.rpn_variables = generate_variables(d)
        self.jinja_env = v
        if d.get("report", "") == "twissReport" and not full:
            return r + self._twiss_simulation()
        return r + self._full_simulation()

    def _abspath(self, basename):
        return _SIM_DATA.lib_file_abspath(basename, qcall=self.qcall)

    def _commands(self):
        commands = self.util.iterate_models(
            CommandIterator(self.filename_map, self._format_field_value),
            "commands",
        ).result
        res = ""
        for c in commands:
            prefix = (
                "! "
                if CommandIterator.IS_DISABLED_FIELD in c[0]
                and c[0][CommandIterator.IS_DISABLED_FIELD] == "1"
                else ""
            )
            res += "\n" + prefix + "&{}".format(c[0]._type) + "\n"
            for f in c[1]:
                res += prefix + "  {} = {},".format(f[0], f[1]) + "\n"
            res += prefix + "&end" + "\n"
        return res

    def _format_field_value(self, state, model, field, el_type):
        def _num(el_type, value):
            return el_type in (
                "RPNValue",
                "RPNBoolean",
                "Integer",
                "Float",
            ) and re.search(r"^[\-\+0-9eE\.]+$", str(value))

        value = model[field]
        if el_type.endswith("StringArray"):
            return ["{}[0]".format(field), value]
        if el_type == "RPNValue":
            if LatticeUtil.is_command(model) and model._type == "run_setup":
                # run_setup RPN values need to be evaluated because the lattice contains
                # the variables and the lattice is not loaded until after run_setup has executed
                value = _format_rpn_value(self._cv.eval_var_with_assert(value))
            else:
                value = _format_rpn_value(
                    value, is_command=LatticeUtil.is_command(model)
                )
        elif el_type in ("OutputFile", "MultiOutputFile"):
            value = state.filename_map[
                LatticeUtil.file_id(model._id, state.field_index)
            ]
        elif el_type.startswith("InputFile"):
            value = self._input_file(
                LatticeUtil.model_name_for_data(model), field, value
            )
            if el_type == "InputFileXY":
                value += "={}+{}".format(model[field + "X"], model[field + "Y"])
            elif (
                el_type == "InputFile"
                and "_type" in model
                and model._type == "run_setup"
                and field == "expand_for"
                and _is_openpmd_file(value)
            ):
                self._openpmd_files.append(value)
                value += ".sdds"
        elif el_type == "BeamInputFile":
            value = self._input_file("bunchFile", "sourceFile", value)
            if _is_openpmd_file(value):
                self._openpmd_files.append(value)
                value += ".sdds"
                model.input_type = "elegant"
        elif el_type == "LatticeBeamlineList":
            value = state.id_map[int(value)].name
        elif el_type == "ElegantLatticeList":
            value = self._lattice_filename(value)
        elif field == "command" and LatticeUtil.model_name_for_data(model) == "SCRIPT":
            for f in ("commandFile", "commandInputFile"):
                if f in model and model[f]:
                    fn = self._input_file(model.type, f, model[f])
                    value = re.sub(r"\b" + re.escape(model[f]) + r"\b", fn, value)
            if model.commandFile:
                value = "./" + value
        if not _num(el_type, value):
            value = '"{}"'.format(value)
        return [field, value]

    def _full_simulation(self):
        def _escape(v):
            return re.sub(r"\\", r"\\\\", v)

        d = self.data
        if not LatticeUtil.find_first_command(d, "global_settings"):
            d.models.commands.insert(
                0,
                PKDict(
                    _id=LatticeUtil.max_id(d) + 1,
                    _type="global_settings",
                ),
            )
        self.jinja_env.update(
            commands=_escape(self._commands()),
            lattice=_escape(self._lattice()),
            simulationMode=d.models.simulation.simulationMode,
            openPMDFiles=self._openpmd_files,
        )
        return template_common.render_jinja(SIM_TYPE, self.jinja_env)

    def _input_file(self, model_name, field, filename):
        return _SIM_DATA.lib_file_name_with_model_field(
            model_name,
            field,
            filename,
        )

    def _lattice(self):
        return self.util.render_lattice_and_beamline(
            lattice.LatticeIterator(self.filename_map, self._format_field_value),
            quote_name=True,
        )

    def _lattice_filename(self, value):
        if value and value == "Lattice":
            return "elegant.lte"
        return value + ".filename.lte"

    def _twiss_simulation(self):
        d = self.data
        max_id = LatticeUtil.max_id(d)
        sim = d.models.simulation
        sim.simulationMode = "serial"
        run_setup = LatticeUtil.find_first_command(d, "run_setup") or PKDict(
            _id=max_id + 1,
            _type="run_setup",
            lattice="Lattice",
            p_central_mev=d.models.bunch.p_central_mev,
        )
        run_setup.use_beamline = sim.activeBeamlineId
        run_setup.always_change_p0 = "0"
        twiss_output = LatticeUtil.find_first_command(d, "twiss_output") or PKDict(
            _id=max_id + 2,
            _type="twiss_output",
        )
        twiss_output.filename = "1"
        twiss_output.final_values_only = "0"
        twiss_output.output_at_each_step = "0"
        change_particle = LatticeUtil.find_first_command(d, "change_particle")
        d.models.commands = [
            run_setup,
            twiss_output,
        ]
        if change_particle:
            d.models.commands.insert(0, change_particle)
        return self._full_simulation()

    def _validate_data(self):
        def _fix(m):
            """the halo(gaussian) value will get validated/escaped to halogaussian, change it back"""
            if "distribution_type" in m and "halogaussian" in m.distribution_type:
                m.distribution_type = m.distribution_type.replace(
                    "halogaussian", "halo(gaussian)"
                )

        enum_info = template_common.validate_models(self.data, SCHEMA)
        _fix(self.data.models.bunch)
        for t in ["elements", "commands"]:
            for m in self.data.models[t]:
                template_common.validate_model(
                    m,
                    SCHEMA.model[LatticeUtil.model_name_for_data(m)],
                    enum_info,
                )
                _fix(m)


def _build_filename_map(data):
    return _build_filename_map_from_util(LatticeUtil(data, SCHEMA))


def _build_filename_map_from_util(util, update_filenames=True):
    return util.iterate_models(OutputFileIterator(update_filenames)).result


def _format_rpn_value(value, is_command=False):
    if code_variable.CodeVar.is_var_value(value):
        value = code_variable.CodeVar.infix_to_postfix(value)
        if is_command:
            return "({})".format(value)
    if value:
        value = re.sub(r"(\d)\.0+$", r"\1", str(value))
    return value


def _get_filename_for_element_id(file_id, data):
    return _build_filename_map(data)[file_id]


def _is_histogram_file(filename, columns):
    filename = os.path.basename(filename)
    if re.search(r"^closed_orbit.output", filename):
        return False
    if "xFrequency" in columns and "yFrequency" in columns:
        return False
    if (
        ("x" in columns and "xp" in columns)
        or ("y" in columns and "yp" in columns)
        or ("t" in columns and "p" in columns)
    ):
        return True
    return False


def _is_openpmd_file(filename):
    if filename:
        return re.search(r"\.h5$", str(filename), re.IGNORECASE)
    return False


def _output_info(run_dir):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))

    def _info(filename, run_dir, file_id):
        def _defs(parameters):
            """Convert parameters to useful definitions"""
            return PKDict(
                {
                    p: PKDict(
                        zip(
                            [
                                "symbol",
                                "units",
                                "description",
                                "format_string",
                                "type",
                                "fixed_value",
                            ],
                            sdds.sddsdata.GetParameterDefinition(_SDDS_INDEX, p),
                        ),
                    )
                    for p in parameters
                }
            )

        def _fix(v):
            if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
                return 0
            return v

        file_path = run_dir.join(filename)
        if not re.search(r".sdds$", filename, re.IGNORECASE):
            return PKDict(
                isAuxFile=True,
                filename=filename,
                id=file_id,
                lastUpdateTime=int(os.path.getmtime(str(file_path))),
            )
        try:
            if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(file_path)) != 1:
                return None
            column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
            plottable_columns = []
            double_column_count = 0
            field_range = PKDict()
            for col in column_names:
                col_type = sdds.sddsdata.GetColumnDefinition(_SDDS_INDEX, col)[4]
                if col_type < _SDDS_STRING_TYPE:
                    plottable_columns.append(col)
                if col_type in _SDDS_DOUBLE_TYPES:
                    double_column_count += 1
                field_range[col] = []
            parameter_names = sdds.sddsdata.GetParameterNames(_SDDS_INDEX)
            parameters = PKDict([(p, []) for p in parameter_names])
            page_count = 0
            row_counts = []
            while True:
                if sdds.sddsdata.ReadPage(_SDDS_INDEX) <= 0:
                    break
                row_counts.append(sdds.sddsdata.RowCount(_SDDS_INDEX))
                page_count += 1
                for i, p in enumerate(parameter_names):
                    parameters[p].append(
                        _fix(sdds.sddsdata.GetParameter(_SDDS_INDEX, i))
                    )
                for col in column_names:
                    try:
                        values = sdds.sddsdata.GetColumn(
                            _SDDS_INDEX,
                            column_names.index(col),
                        )
                    except SystemError:
                        # incorrectly generated sdds file
                        break
                    if not values:
                        pass
                    elif field_range[col]:
                        field_range[col][0] = min(
                            _fix(min(values)), field_range[col][0]
                        )
                        field_range[col][1] = max(
                            _fix(max(values)), field_range[col][1]
                        )
                    else:
                        field_range[col] = [_fix(min(values)), _fix(max(values))]
            return PKDict(
                isAuxFile=False if double_column_count > 1 else True,
                filename=filename,
                id=file_id,
                rowCounts=row_counts,
                pageCount=page_count,
                columns=column_names,
                parameters=parameters,
                parameterDefinitions=_defs(parameters),
                latticeId=LatticeUtil.get_lattice_id_from_file_id(data, file_id),
                plottableColumns=plottable_columns,
                lastUpdateTime=int(os.path.getmtime(str(file_path))),
                isHistogram=_is_histogram_file(filename, column_names),
                fieldRange=field_range,
            )
        finally:
            try:
                sdds.sddsdata.Terminate(_SDDS_INDEX)
            except Exception:
                pass
        return None

    # cache outputInfo to file, used later for report frames
    info_file = run_dir.join(_OUTPUT_INFO_FILE)
    if os.path.isfile(str(info_file)):
        try:
            res = simulation_db.read_json(info_file)
            if not res or res[0].get("_version", "") == _OUTPUT_INFO_VERSION:
                return res
        except ValueError as e:
            pass
    _sdds_init()
    res = []
    filename_map = _build_filename_map(data)
    for k in filename_map.keys_in_order:
        filename = filename_map[k]
        fn = filename % 1 if _is_multifile(filename) else filename
        if not run_dir.join(fn).exists():
            continue
        info = _info(fn, run_dir, k)
        if info:
            info.modelKey = LatticeUtil.output_model_name(info.id)
            if _is_multifile(filename):
                info.filename = filename
                info.pageCount = _multifile_count(run_dir, filename)
            res.append(info)
    if res:
        res[0]["_version"] = _OUTPUT_INFO_VERSION
    simulation_db.write_json(info_file, res)
    return res


def _parse_elegant_log(run_dir):
    path = run_dir.join(ELEGANT_LOG_FILE)
    if not path.exists():
        return "", 0, 0
    res = ""
    last_element = None
    text = pkio.read_text(str(path))
    want_next_line = False
    prev_line = ""
    prev_err = ""
    step = 0
    for line in text.split("\n"):
        if line == prev_line:
            continue
        match = re.search(r"^Starting (\S+) at s=", line)
        if match:
            name = match.group(1)
            if not re.search(r"^M\d+\#", name):
                last_element = name
        match = re.search(r"^tracking step (\d+)", line)
        if match:
            step = int(match.group(1))
        if want_next_line:
            res += line + "\n"
            want_next_line = False
        elif _ERROR_IGNORE_RE.search(line):
            pass
        elif _ERROR_RE.search(line):
            if len(line) < 10:
                want_next_line = True
            else:
                if line != prev_err:
                    res += line + "\n"
                prev_err = line
        prev_line = line
    return res, last_element, step


def _prepare_bunch_simulation(data):
    state = PKDict(next_id=0)

    def new_model(name, type_field="_type", id_field="_id"):
        state.next_id += 1
        res = _SIM_DATA.model_defaults(name).pkupdate(
            {
                id_field: state.next_id,
            }
        )
        if type_field:
            res[type_field] = name.replace("command_", "")
        return res

    data.models.elements = [
        new_model("WATCH", type_field="type").pkupdate(
            name="W1",
            filename="1",
        )
    ]
    data.models.beamlines = [
        new_model("beamline", type_field="", id_field="id").pkupdate(
            name="bl",
            items=[data.models.elements[0]._id],
        )
    ]
    bc = None
    expand_for = ""
    if data.models.bunchSource.inputSource == "bunched_beam":
        bc = LatticeUtil.find_first_command(data, "bunched_beam")
        bc.use_twiss_command_values = "0"
    else:
        bc = LatticeUtil.find_first_command(data, "sdds_beam")
        expand_for = LatticeUtil.find_first_command(data, "run_setup").expand_for
    data.models.commands = [
        new_model("command_run_setup").pkupdate(
            lattice="Lattice",
            use_beamline=data.models.beamlines[0].id,
            p_central_mev=data.models.bunch.p_central_mev,
            expand_for=expand_for,
        ),
        new_model("command_run_control"),
        bc,
        new_model("command_track"),
    ]


def _report_output_filename(report):
    if report == "twissReport":
        return "twiss_output.filename.sdds"
    return "W1.filename-001.sdds"


def _sdds_beam_type(column_names):
    def _contains(column_names, search):
        for col in search:
            if col not in column_names:
                return False
        return True

    if _contains(column_names, ["x", "xp", "y", "yp", "t", "p"]):
        return "elegant"
    if _contains(column_names, ["r", "pr", "pz", "t", "pphi"]):
        return "spiffe"
    return ""


def _sdds_beam_type_from_file(path):
    if _is_openpmd_file(path):
        return "openPMD"
    _sdds_init()
    res = ""
    if sdds.sddsdata.InitializeInput(_SDDS_INDEX, str(path)) == 1:
        res = _sdds_beam_type(sdds.sddsdata.GetColumnNames(_SDDS_INDEX))
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return res


def _sdds_init():
    global _SDDS_INDEX, _SDDS_DOUBLE_TYPES, _SDDS_STRING_TYPE, sdds_util, sdds
    if _SDDS_INDEX is not None:
        return
    from sirepo.template import sdds_util
    import sdds

    _SDDS_INDEX = 0
    _s = sdds.SDDS(_SDDS_INDEX)
    _x = getattr(_s, "SDDS_LONGDOUBLE", None)
    _SDDS_DOUBLE_TYPES = [_s.SDDS_DOUBLE, _s.SDDS_FLOAT] + ([_x] if _x else [])
    _SDDS_STRING_TYPE = _s.SDDS_STRING


def analysis_job_log_to_html(data, run_dir, **kwargs):
    return PKDict(
        html=pygments.highlight(
            pkio.read_text(run_dir.join(ELEGANT_LOG_FILE)),
            pygments.lexers.get_lexer_by_name("text"),
            pygments.formatters.HtmlFormatter(
                noclasses=False,
                linenos=False,
            ),
        )
    )


def _is_multifile(filename):
    return "%" in filename


def _multifile_count(run_dir, filename):
    fn = re.sub(r"\%.*?\.", "*.", filename)
    c = 0
    for f in glob.glob(str(run_dir.join(fn))):
        c += 1
    return c
