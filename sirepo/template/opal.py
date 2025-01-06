"""OPAL execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import hdf5_util
from sirepo.template import lattice
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
from sirepo.template.madx_converter import MadxConverter
import math
import numpy as np
import re
import sirepo.const
import sirepo.lib
import sirepo.sim_data
import os.path


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
_OPAL_H5_FILE = "opal.h5"
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


class OpalMadxConverter(MadxConverter):
    _FIELD_MAP = [
        [
            "DRIFT",
            ["DRIFT", "l"],
        ],
        [
            "SBEND",
            ["SBEND", "l", "angle", "e1", "e2", "gap=hgap", "psi=tilt"],
        ],
        [
            "RBEND",
            ["RBEND", "l", "angle", "e1", "gap=hgap", "psi=tilt"],
        ],
        [
            "QUADRUPOLE",
            ["QUADRUPOLE", "l", "k1", "k1s", "psi=tilt"],
        ],
        [
            "SEXTUPOLE",
            ["SEXTUPOLE", "l", "k2", "k2s", "psi=tilt"],
        ],
        [
            "OCTUPOLE",
            ["OCTUPOLE", "l", "k3", "k3s", "psi=tilt"],
        ],
        [
            "SOLENOID",
            # TODO(pjm): compute dks from ksi?
            ["SOLENOID", "l", "ks"],
        ],
        [
            "MULTIPOLE",
            # TODO(pjm): compute kn, ks from knl, ksl?
            ["MULTIPOLE", "psi=tilt"],
        ],
        [
            "HKICKER",
            ["HKICKER", "l", "kick", "psi=tilt"],
        ],
        [
            "VKICKER",
            ["VKICKER", "l", "kick", "psi=tilt"],
        ],
        [
            "KICKER",
            ["KICKER", "l", "hkick", "vkick", "psi=tilt"],
        ],
        [
            "MARKER",
            ["MARKER"],
        ],
        [
            "PLACEHOLDER",
            ["DRIFT", "l"],
        ],
        [
            "INSTRUMENT",
            ["DRIFT", "l"],
        ],
        [
            "ECOLLIMATOR",
            ["ECOLLIMATOR", "l", "xsize", "ysize"],
        ],
        [
            "RCOLLIMATOR",
            ["RCOLLIMATOR", "l", "xsize", "ysize"],
        ],
        [
            "COLLIMATOR apertype=ELLIPSE",
            ["ECOLLIMATOR", "l", "xsize", "ysize"],
        ],
        [
            "COLLIMATOR apertype=RECTANGLE",
            ["RCOLLIMATOR", "l", "xsize", "ysize"],
        ],
        [
            "RFCAVITY",
            ["RFCAVITY", "l", "volt", "lag", "freq"],
        ],
        [
            "TWCAVITY",
            ["TRAVELINGWAVE", "l", "volt", "lag", "freq", "dlag=delta_lag"],
        ],
        [
            "HMONITOR",
            ["MONITOR", "l"],
        ],
        [
            "VMONITOR",
            ["MONITOR", "l"],
        ],
        [
            "MONITOR",
            ["MONITOR", "l"],
        ],
    ]

    def __init__(self, qcall, **kwargs):
        super().__init__(SIM_TYPE, self._FIELD_MAP, qcall=qcall, **kwargs)

    def to_madx(self, data):
        def _get_len_by_id(data, id):
            for e in data.models.elements:
                if e._id == id:
                    return e.l
            raise AssertionError(
                f"id={id} not found in elements={data.models.elements}"
            )

        def _get_element_type(data, id):
            for e in data.models.elements:
                if e._id == id:
                    return e.type
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

        def _get_distance_and_insert_drift(beamline, beam_idx):
            for i, e in enumerate(beamline["items"]):
                if i + 1 == len(beamline["items"]):
                    break
                if _get_element_type(data, e) == "DRIFT":
                    continue
                p = beamline.positions[i].elemedge
                n = beamline.positions[i + 1].elemedge
                l = code_var(data.models.rpnVariables).eval_var(_get_len_by_id(data, e))
                d = round(float(n) - float(p) - l[0], 10)
                if d > 0:
                    _insert_drift(d, beam_idx, i, p, l)

        if data.models.simulation.elementPosition == "absolute":
            for j, b in enumerate(data.models.beamlines):
                _get_distance_and_insert_drift(b, j)
        madx = super().to_madx(data)
        mb = LatticeUtil.find_first_command(madx, "beam")
        ob = LatticeUtil.find_first_command(data, "beam")
        for f in ob:
            if f in mb and f in SCHEMA.model.command_beam:
                mb[f] = ob[f]
                if f in ("gamma", "energy", "pc") and mb[f]:
                    madx.models.bunch.beamDefinition = f
        od = LatticeUtil.find_first_command(data, "distribution")
        # TODO(pjm): save dist in vars
        return madx

    def from_madx(self, madx):
        data = self.fill_in_missing_constants(super().from_madx(madx), _OPAL_CONSTANTS)
        data.models.simulation.elementPosition = "relative"
        mb = LatticeUtil.find_first_command(madx, "beam")
        LatticeUtil.find_first_command(data, "option").version = 20000
        LatticeUtil.find_first_command(data, "beam").particle = mb.particle.upper()
        LatticeUtil.find_first_command(data, "beam").pc = self.particle_energy.pc
        LatticeUtil.find_first_command(data, "track").line = (
            data.models.simulation.visualizationBeamlineId
        )
        self.__fixup_distribution(madx, data)
        return data

    def _fixup_element(self, element_in, element_out):
        super()._fixup_element(element_in, element_out)
        if self.from_class.sim_type() == SIM_TYPE:
            pass
        else:
            if element_in.type == "SBEND":
                angle = self.__val(element_in.angle)
                if angle != 0:
                    length = self.__val(element_in.l)
                    d1 = 2 * length / angle
                    element_out.l = d1 * math.sin(length / d1)
            if element_in.type in ("SBEND", "RBEND"):
                # kinetic energy in MeV
                element_out.designenergy = round(
                    (self.particle_energy.energy - self.beam.mass) * 1e3,
                    6,
                )
                element_out.gap = 2 * self.__val(element_in.hgap)
                # element_out.fmapfn = "hard_edge_profile.txt"
            if element_in.type == "QUADRUPOLE":
                k1 = self.__val(element_out.k1)
                if self.beam.charge < 0:
                    k1 *= -1
                element_out.k1 = "{} * {}".format(k1, self._var_name("brho"))

    def __fixup_distribution(self, madx, data):
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
        for dim in ("x", "y"):
            self._replace_var(data, f"emit_{dim}", mb[f"e{dim}"])
            beta = self._find_var(madx, f"beta_{dim}")
            if beta:
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
        if self._find_var(madx, "dp_s_coupling"):
            dist.corrz = self._var_name("dp_s_coupling")
        ob = LatticeUtil.find_first_command(data, "beam")
        ob.bcurrent = mb.bcurrent
        if self._find_var(madx, "n_particles_per_bunch"):
            ob.npart = self._var_name("n_particles_per_bunch")
        dist.sigmaz = self.__val(mb.sigt)
        dist.sigmapz = "{} * {} * {}".format(
            mb.sige, self._var_name("beta"), self._var_name("gamma")
        )

    def __val(self, var_value):
        return self.vars.eval_var_with_assert(var_value)


def analysis_job_compute_particle_ranges(data, run_dir, **kwargs):
    return template_common.compute_field_range(
        data,
        _compute_range_across_frames,
        run_dir,
    )


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if is_running:
        data = _SIM_DATA.sim_run_input(run_dir)
        # TODO(pjm): determine total frame count and set percentComplete
        res.frameCount = read_frame_count(run_dir) - 1
        return res
    if _SIM_DATA.sim_run_input(run_dir, checked=False):
        res.frameCount = read_frame_count(run_dir)
        if res.frameCount > 0:
            res.percentComplete = 100
            res.outputInfo = _output_info(run_dir)
    return res


def bunch_plot(model, run_dir, frame_index, filename=_OPAL_H5_FILE):
    def _points(file, frame_index, name):
        return np.array(file["/Step#{}/{}".format(frame_index, name)])

    def _title(file, frame_index):
        t = "Step {}".format(frame_index)
        if "SPOS" in file["/Step#{}".format(frame_index)].attrs:
            t += ", SPOS {0:.5f}m".format(
                file["/Step#{}".format(frame_index)].attrs["SPOS"][0]
            )
        return t

    return hdf5_util.HDF5Util(str(run_dir.join(filename))).heatmap(
        PKDict(
            format_plot=_units_from_hdf5,
            frame_index=frame_index,
            model=model,
            points=_points,
            title=_title,
        )
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
        return _OPAL_H5_FILE
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


def read_frame_count(run_dir):
    def _walk_file(h5file, key, step, res):
        if key:
            res[0] = step + 1

    try:
        return _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, [0])[0]
    except IOError:
        pass
    return 0


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
    # elementAnimations
    return bunch_plot(
        frame_args,
        frame_args.run_dir,
        frame_args.frameIndex,
        _file_name_for_element_animation(frame_args),
    )


def sim_frame_beamline3dAnimation(frame_args):
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


def sim_frame_plotAnimation(frame_args):
    def _walk_file(h5file, key, step, res):
        if key:
            for field in res.values():
                field.points.append(h5file[key].attrs[field.name][field.index])
        else:
            for field in res.values():
                _units_from_hdf5(h5file, field)

    return hdf5_util.HDF5Util(frame_args.run_dir.join(_OPAL_H5_FILE)).lineplot(
        PKDict(
            model=frame_args,
            index=lambda parts: _DIM_INDEX[parts[1]] if len(parts) > 1 else 0,
            format_plots=lambda h5file, plots: _iterate_hdf5_steps_from_handle(
                h5file,
                _walk_file,
                plots,
            ),
        )
    )


def sim_frame_plot2Animation(frame_args):
    from sirepo.template import sdds_util

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
        missing_files = []
        for infile in input_files:
            if not _SIM_DATA.lib_file_exists(infile.lib_filename):
                missing_files.append(infile)
        if missing_files:
            return PKDict(
                missingFiles=missing_files,
                imported_data=res,
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
        raise IOError(
            f"invalid file={data.args.basename} extension, expecting .in, .ele, .lte or .madx"
        )
    return PKDict(imported_data=res)


def write_parameters(data, run_dir, is_parallel):
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


def _compute_3d_bounds(run_dir):
    res = []
    p = run_dir.join("data/opal_ElementPositions.txt")
    with pkio.open_text(p) as f:
        for line in f:
            m = re.search(r'^".*?"\s+(\S*?)\s+(\S*?)\s+(\S*?)\s*$', line)
            if m:
                res.append([float(v) for v in (m.group(1), m.group(2), m.group(3))])
    res = np.array(res)
    bounds = []
    for n in range(3):
        v = res[:, n]
        bounds.append([min(v), max(v)])
    return bounds


def _generate_parameters_file(data, qcall=None):
    return _Generate(data, qcall=qcall).sim()


def _compute_range_across_frames(run_dir, **kwargs):
    def _walk_file(h5file, key, step, res):
        if key:
            for field in res:
                v = np.array(h5file["/{}/{}".format(key, field)])
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
    return _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, res)


def _column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, "invalid col: {}".format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def _field_units(units, field):
    if units == "1":
        units = ""
    elif units[0] == "M" and len(units) > 1:
        units = re.sub(r"^.", "", units)
        field.points = (np.array(field.points) * 1e6).tolist()
    elif units[0] == "G" and len(units) > 1:
        units = re.sub(r"^.", "", units)
        field.points = (np.array(field.points) * 1e9).tolist()
    elif units == "ns":
        units = "s"
        field.points = (np.array(field.points) / 1e9).tolist()
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
                if item.type == "SBEND" and run_method == "THICK":
                    # use arclength for SBEND with THICK tracker (only?)
                    angle = code_var.eval_var_with_assert(item.angle)
                    length = angle * length / (2 * math.sin(angle / 2))
                visited.add(item_id)
            edge += length
        else:
            # beamline
            text, edge, names, visited = _generate_beamline(
                util, code_var, item_id, count_by_name, edge, names, visited
            )
            res += text
    return res, edge, names, visited


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
    # TODO(pjm): cache to file with version, similar to template.elegant
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


def _read_data_file(path):
    col_names = []
    rows = []
    with pkio.open_text(str(path)) as f:
        col_names = []
        rows = []
        mode = ""
        for line in f:
            if "---" in line:
                if mode == "header":
                    mode = "data"
                elif mode == "data":
                    break
                if not mode:
                    mode = "header"
                continue
            line = re.sub("\0", "", line)
            if mode == "header":
                col_names = re.split(r"\s+", line.lower())
            elif mode == "data":
                # TODO(pjm): separate overlapped columns. Instead should explicitly set field dimensions
                line = re.sub(r"(\d)(\-\d)", r"\1 \2", line)
                line = re.sub(r"(\.\d{3})(\d+\.)", r"\1 \2", line)
                rows.append(re.split(r"\s+", line))
    return col_names, rows


def _units_from_hdf5(h5file, field):
    return _field_units(
        pkcompat.from_bytes(h5file.attrs["{}Unit".format(field.name)]), field
    )
