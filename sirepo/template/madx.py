"""MAD-X execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import lattice
from sirepo.template import madx_parser
from sirepo.template import opal_parser
from sirepo.template import particle_beam
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import copy
import functools
import h5py
import math
import numpy
import os.path
import pmd_beamphysics.readers
import pykern.pkinspect
import re
import sirepo.lib
import sirepo.sim_data


_BUNCH_PARTICLES_FILE = "ptc_particles.json"

MADX_INPUT_FILE = "in.madx"

MADX_LOG_FILE = "madx.log"

_PTC_PARTICLES_FILE = "ptc_particles.madx"

PTC_LAYOUT_COMMAND = "ptc_create_layout"

_ALPHA_COLUMNS = ["name", "keyword", "parent", "comments", "number", "turn", ""]

_FIELD_UNITS = PKDict(
    betx="m",
    bety="m",
    dx="m",
    dy="m",
    mux="2π",
    muy="2π",
    s="m",
    x="m",
    y="m",
    t="m",
    x0="m",
    y0="m",
)

_PI = 4 * math.atan(1)

MADX_CONSTANTS = PKDict(
    pi=_PI,
    twopi=_PI * 2.0,
    raddeg=_PI / 180.0,
    degrad=180 / _PI,
    e=math.exp(1),
    emass=0.510998928e-03,
    pmass=0.938272046e00,
    nmass=0.931494061 + 00,
    mumass=0.1056583715,
    clight=299792458.0,
    qelect=1.602176565e-19,
    hbar=6.58211928e-25,
    erad=2.8179403267e-15,
)

_OUTPUT_INFO_FILE = "outputInfo.json"

_OUTPUT_INFO_VERSION = "1"

_END_MATCH_COMMAND = "endmatch"

_PTC_TRACK_COMMAND = "ptc_track"

_PTC_TRACKLINE_COMMAND = "ptc_trackline"

SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

PTC_OBSERVE_TWISS_COLS = [
    "W",
    "alfx",
    "alfy",
    "betx",
    "bety",
    "ct0",
    "ctct",
    "ctpt",
    "emit_t",
    "emit_x",
    "emit_y",
    "eta_px",
    "eta_py",
    "eta_x",
    "eta_y",
    "gamma_x",
    "gamma_y",
    "n",
    "pt0",
    "ptpt",
    "px0",
    "pxct",
    "pxpt",
    "pxpx",
    "pxpy",
    "pxy",
    "py0",
    "pyct",
    "pypt",
    "pypy",
    "s",
    "sx",
    "sy",
    "x0",
    "xct",
    "xpt",
    "xpx",
    "xpy",
    "xx",
    "xy",
    "y0",
    "yct",
    "ypt",
    "ypy",
    "yy",
]


_TFS_FILE_EXTENSION = "tfs"

_TWISS_OUTPUT_FILE = f"twiss.{_TFS_FILE_EXTENSION}"


class LibAdapter(sirepo.lib.LibAdapterBase):
    def parse_file(self, path):
        from sirepo.template import madx_parser

        return self._convert(madx_parser.parse_file(pkio.read_text(path)))

    def write_files(self, data, source_path, dest_dir):
        """writes files for the simulation

        Returns:
            PKDict: structure of files written (debugging only)
        """
        pkio.write_text(
            dest_dir.join(source_path.basename),
            generate_parameters_file(data),
        )
        if data.models.bunch.beamDefinition == "file":
            f = SIM_DATA.lib_file_name_with_model_field(
                "bunch", "sourceFile", data.models.bunch.sourceFile
            )
            d = dest_dir.join(f)
            pykern.pkio.mkdir_parent_only(d)
            d.mksymlinkto(source_path.dirpath().join(f), absolute=False)
        if LatticeUtil.find_first_command(data, PTC_LAYOUT_COMMAND):
            generate_ptc_particles_file(dest_dir, data, None)
        return PKDict()


class _MadxLogParser(template_common.LogParser):
    def _parse_log_line(self, line):
        if re.search(r"^\++ (error|warning):", line, re.IGNORECASE):
            return re.sub(r"^\++ ", "", line) + "\n"
        elif re.search(r"^\+.*? fatal:", line, re.IGNORECASE):
            return re.sub(r"^.*? ", "", line) + "\n"
        return None


class MadxOutputFileIterator(lattice.ModelIterator):
    def __init__(self):
        self.result = PKDict(
            keys_in_order=[],
        )
        self.model_index = PKDict()

    def field(self, model, field_schema, field):
        if field == lattice.ElementIterator.IS_DISABLED_FIELD or field == "_super":
            return
        self.field_index += 1
        if field_schema[1] == "OutputFile":
            b = "{}{}.{}".format(
                model._type,
                (
                    self.model_index[self.model_name]
                    if self.model_index[self.model_name] > 1
                    else ""
                ),
                field,
            )
            k = LatticeUtil.file_id(model._id, self.field_index)
            self.result[k] = PKDict(
                filename=b + f".{_TFS_FILE_EXTENSION}",
                model_type=model._type,
                purebasename=b,
                ext=_TFS_FILE_EXTENSION,
            )
            self.result.keys_in_order.append(k)

    def start(self, model):
        self.field_index = 0
        self.model_name = LatticeUtil.model_name_for_data(model)
        if self.model_name in self.model_index:
            self.model_index[self.model_name] += 1
        else:
            self.model_index[self.model_name] = 1


def add_observers(util, etype=None):
    def _command_index(commands):
        for i, c in enumerate(commands):
            if c._type == "ptc_create_universe":
                break
        else:
            raise AssertionError(
                f"no ptc_create_universe command found in commands={util.data.models.commands}",
            )
        return i + 1

    i = _command_index(util.data.models.commands)
    name_count = PKDict()
    oid = util.max_id
    for bid in util.explode_beamline(
        util.data.models.simulation.visualizationBeamlineId
    ):
        e = util.get_item(bid)
        if etype and e.type != etype:
            continue
        if e.type == "INSTRUMENT" or "MONITOR" in e.type:
            # always include instrument and monitor positions
            pass
        elif not e.get("l", 0):
            continue
        oid += 1
        count = name_count.get(e.name, 0) + 1
        name_count[e.name] = count
        util.data.models.commands.insert(
            i,
            PKDict(
                _id=oid,
                _type="ptc_observe",
                place=f"{e.name}[{count}]",
            ),
        )
        i += 1


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        outputInfo=_output_info(run_dir),
    )


def code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(MADX_CONSTANTS),
        case_insensitive=True,
    )


def command_template(name, next_id, beamline_id=None):
    def _set_defaults(command, state):
        command._id = state.next_id
        state.next_id += 1
        SIM_DATA.update_model_defaults(command, f"command_{command._type}")
        return command

    if name == "particle":
        c = [
            PKDict(_type="option", echo="0", info="0"),
            PKDict(_type="ptc_create_universe", sector_nmul=10, sector_nmul_max=10),
            PKDict(_type="ptc_create_layout", method=4, nst=25),
            PKDict(
                _type="ptc_track",
                element_by_element="1",
                file="1",
                icase="6",
                maxaper="1,1,1,1,5,1",
            ),
            PKDict(_type="ptc_track_end"),
            PKDict(_type="ptc_end"),
        ]
    elif name == "matching":
        c = [
            PKDict(_type="match", sequence=beamline_id),
            PKDict(_type="vary", step=1e-5),
            PKDict(_type="lmdif", calls=50, tolerance=1e-8),
            PKDict(_type="endmatch"),
        ]
    state = PKDict(
        next_id=next_id,
    )
    return [_set_defaults(v, state) for v in c]


def eval_code_var(data):
    # TODO(e-carlin): When #3111 is merged use the code in LibAdapterBase._convert
    # to do this work. It is copied from there.
    cv = code_var(data.models.rpnVariables)

    def _model(model, name):
        schema = SCHEMA.model[name]

        k = x = v = None
        try:
            for k, x in schema.items():
                t = x[1]
                v = model[k] if k in model else x[2]
                if t == "RPNValue":
                    t = "Float"
                    if cv.is_var_value(v):
                        model[k] = cv.eval_var_with_assert(v)
                        continue
                if t == "Float":
                    model[k] = float(v) if v else 0.0
                elif t == "Integer":
                    model[k] = int(v) if v else 0
        except Exception as e:
            pkdlog("model={} field={} decl={} value={} exception={}", name, k, x, v, e)
            raise

    for x in data.models.rpnVariables:
        x.value = cv.eval_var_with_assert(x.value)
    for k, v in data.models.items():
        if k in SCHEMA.model:
            _model(v, k)
    for x in ("elements", "commands"):
        for m in data.models[x]:
            _model(m, LatticeUtil.model_name_for_data(m))


def extract_parameter_report(
    data, run_dir=None, filename=_TWISS_OUTPUT_FILE, results=None
):
    if not results:
        assert (
            run_dir and filename
        ), f"must supply either results or run_dir={run_dir} and filename={filename}"
    t = results or madx_parser.parse_tfs_file(run_dir.join(filename))
    plots = []
    m = data.models[data.report]
    for f in ("y1", "y2", "y3"):
        if m[f] == "None":
            continue
        if m[f] not in t:
            return PKDict(
                error=f'Missing column "{m[f]}" in report output file.',
            )
        plots.append(
            PKDict(field=m[f], points=to_floats(t[m[f]]), label=field_label(m[f])),
        )
    x = m.get("x", "s")
    res = template_common.parameter_plot(
        to_floats(t[x]),
        plots,
        m,
        PKDict(
            y_label="",
            x_label=field_label(x),
            dynamicYLabel=True,
        ),
    )
    if filename == _TWISS_OUTPUT_FILE and not results:
        res.initialTwissParameters = PKDict(
            betx=t.betx[0],
            bety=t.bety[0],
            alfx=t.alfx[0],
            alfy=t.alfy[0],
            x=t.x[0],
            y=t.y[0],
            px=t.px[0],
            py=t.py[0],
        )
    return res


def field_label(field):
    if field in _FIELD_UNITS:
        return "{} [{}]".format(field, _FIELD_UNITS[field])
    return field


def file_info(filename, run_dir, file_id):
    path = str(run_dir.join(filename))
    plottable = []
    tfs = madx_parser.parse_tfs_file(path)
    for f in tfs:
        if f in _ALPHA_COLUMNS:
            continue
        v = to_floats(tfs[f])
        if numpy.any(v):
            plottable.append(f)
    count = 1
    if "turn" in tfs:
        info = madx_parser.parse_tfs_page_info(path)
        count = len(info)
    return PKDict(
        modelKey="elementAnimation{}".format(file_id),
        filename=filename,
        isHistogram=not _is_parameter_report_file(filename),
        plottableColumns=plottable,
        pageCount=count,
    )


def generate_parameters_file(data):
    data = _iterate_and_format_rpns(data, SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    util = LatticeUtil(data, SCHEMA)
    if data.models.simulation.computeTwissFromParticles == "1":
        add_observers(util)
    filename_map = _build_filename_map_from_util(util)
    report = data.get("report", "")
    v.twissOutputFilename = _TWISS_OUTPUT_FILE
    v.lattice = _generate_lattice(filename_map, util)
    v.variables = code_var(data.models.rpnVariables).generate_variables(
        _generate_variable
    )
    v.useBeamline = util.select_beamline().name
    if report == "twissReport" or _is_report("bunchReport", report):
        v.twissOutputFilename = _TWISS_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, "twiss.madx")
    _add_commands(data, util)
    v.commands = _generate_commands(filename_map, util)
    v.hasTwiss = bool(util.find_first_command(data, "twiss"))
    if not v.hasTwiss:
        v.twissOutputFilename = _TWISS_OUTPUT_FILE
    return template_common.render_jinja(SIM_TYPE, v, "parameters.madx")


def generate_ptc_particles_file(run_dir, data, twiss):
    bunch = data.models.bunch
    v = None
    if bunch.beamDefinition == "file":
        v = _read_bunch_file(
            run_dir.join(
                SIM_DATA.lib_file_name_with_model_field(
                    "bunch", "sourceFile", bunch.sourceFile
                )
            ),
            _read_particles,
        )
        v.t = list(-numpy.array(v.t))
    else:
        beam = LatticeUtil.find_first_command(data, "beam")
        c = code_var(data.models.rpnVariables)
        p = particle_beam.populate_uncoupled_beam(
            bunch.numberOfParticles,
            float(bunch.betx),
            float(bunch.alfx),
            float(c.eval_var_with_assert(beam.ex)),
            float(bunch.bety),
            float(bunch.alfy),
            c.eval_var_with_assert(beam.ey),
            c.eval_var_with_assert(beam.sigt),
            c.eval_var_with_assert(beam.sige),
            iseed=bunch.randomSeed,
        )
        v = PKDict(
            x=to_floats(p[:, 0] + float(bunch.x)),
            px=to_floats(p[:, 1] + float(bunch.px)),
            y=to_floats(p[:, 2] + float(bunch.y)),
            py=to_floats(p[:, 3] + float(bunch.py)),
            t=to_floats(p[:, 4]),
            pt=to_floats(p[:, 5]),
        )
    if "report" in data and "bunchReport" in data.report:
        v.summaryData = twiss
        simulation_db.write_json(run_dir.join(_BUNCH_PARTICLES_FILE), v)
    r = ""
    for i in range(len(v.x)):
        r += "ptc_start"
        for f in ("x", "px", "y", "py", "t", "pt"):
            r += f", {f}={v[f][i]}"
        r += ";\n"
    pkio.write_text(run_dir.join(_PTC_PARTICLES_FILE), r)


def get_data_file(run_dir, model, frame, options):
    if _is_report("bunchReport", model):
        return _PTC_PARTICLES_FILE
    if frame == SCHEMA.constants.logFileFrameId:
        return template_common.text_data_file(MADX_LOG_FILE, run_dir)
    if frame >= 0:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        if model == "twissFromParticlesAnimation":
            return [
                f.filename
                for f in _build_filename_map(data).values()
                if hasattr(f, "get") and f.get("model_type") == _PTC_TRACK_COMMAND
            ][-1]
        return _get_filename_for_element_id(
            re.sub(r"elementAnimation", "", model),
            data,
        ).filename
    raise AssertionError(f"invalid model={model}")


def post_execution_processing(success_exit, run_dir, **kwargs):
    if success_exit:
        return None
    return _MadxLogParser(run_dir, log_filename=MADX_LOG_FILE).parse_for_errors()


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def prepare_sequential_output_file(run_dir, data):
    r = data.report
    if r == "twissReport" or _is_report("bunchReport", r):
        f = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if f.exists():
            f.remove()
            try:
                save_sequential_report_data(data, run_dir)
            except IOError:
                # the output file isn't readable
                pass


# TODO(e-carlin): fixme - I don't return python
def python_source_for_model(data, model, qcall, **kwargs):
    return generate_parameters_file(data)


def sim_frame(frame_args):
    d = frame_args.sim_in
    d.report = frame_args.frameReport
    d.models[d.report] = frame_args
    return _extract_report_data(d, frame_args.run_dir)


def save_sequential_report_data(data, run_dir):
    template_common.write_sequential_result(
        _extract_report_data(data, run_dir),
        run_dir=run_dir,
    )


def stateless_compute_calculate_bunch_parameters(data, **kwargs):
    return _calc_bunch_parameters(
        data.args.bunch, data.args.command_beam, data.args.variables
    )


def stateless_compute_command_template(data, **kwargs):
    return PKDict(
        commands=command_template(
            data.args.commandTemplate, data.args.nextId, data.args.beamlineId
        ),
    )


def stateful_compute_import_file(data, **kwargs):
    if data.args.ext_lower == ".in":
        from sirepo.template.opal import OpalMadxConverter

        return PKDict(
            imported_data=OpalMadxConverter(qcall=None).to_madx(
                opal_parser.parse_file(
                    data.args.file_as_str,
                    filename=data.args.basename,
                )[0]
            )
        )
    elif data.args.ext_lower == ".ele":
        from sirepo.template import elegant

        return elegant.elegant_file_import(data)
    elif data.args.ext_lower == ".lte":
        from sirepo.template import elegant

        return PKDict(
            imported_data=elegant.ElegantMadxConverter(qcall=None).to_madx(
                elegant.elegant_file_import(data).imported_data
            )
        )
    elif data.args.ext_lower in (".madx", ".seq"):
        d = madx_parser.parse_file(data.args.file_as_str, downcase_variables=True)
        d.models.simulation.name = data.args.purebasename
        return PKDict(imported_data=d)
    raise AssertionError(
        f"invalid file={data.args.basename}, expecting .madx, .seq, .in or .ele/.lte"
    )


def to_float(value):
    return float(value)


def to_floats(values):
    return [to_float(v) for v in values]


def to_string(value):
    return value.replace('"', "")


def write_parameters(data, run_dir, is_parallel, filename=MADX_INPUT_FILE):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    if _is_report("bunchReport", data.report):
        # these reports don't need to run madx
        return
    pkio.write_text(
        run_dir.join(filename),
        # generate_parameters_file may modify data and pkcli.madx may call
        # write_parameters multiple times so make a copy
        generate_parameters_file(copy.deepcopy(data)),
    )


def _add_commands(data, util):
    commands = data.models.commands
    # set the selected beamline depending on the lattice or visualization
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == "beam")
    commands.insert(
        idx + 1,
        PKDict(
            _type="use",
            sequence=util.select_beamline().id,
            _id=LatticeUtil.max_id(data),
        ),
    )
    if not util.find_first_command(data, PTC_LAYOUT_COMMAND):
        return
    # insert call for particles after ptc_create_layout
    idx = next(i for i, cmd in enumerate(commands) if cmd._type == PTC_LAYOUT_COMMAND)
    commands.insert(
        idx + 1,
        PKDict(
            _type="call",
            file=_PTC_PARTICLES_FILE,
            _id=LatticeUtil.max_id(data),
        ),
    )


def _build_filename_map(data):
    return _build_filename_map_from_util(LatticeUtil(data, SCHEMA))


def _build_filename_map_from_util(util):
    return util.iterate_models(MadxOutputFileIterator()).result


def _calc_bunch_parameters(bunch, beam, variables):
    try:
        field = bunch.beamDefinition
        cv = code_var(variables)
        energy = template_common.ParticleEnergy.compute_energy(
            SIM_TYPE,
            beam.particle,
            PKDict(
                {
                    "mass": cv.eval_var_with_assert(beam.mass),
                    "charge": cv.eval_var_with_assert(beam.charge),
                    field: cv.eval_var_with_assert(beam[field]),
                }
            ),
        )
        for f in energy:
            # don't overwrite mass or charge
            if f in ("mass", "charge"):
                continue
            if f in beam and f != field:
                beam[f] = energy[f]
    except AssertionError:
        pass
    return PKDict(command_beam=beam)


def _extract_report_bunchReport(data, run_dir):
    parts = simulation_db.read_json(run_dir.join(_BUNCH_PARTICLES_FILE))
    m = data.models[data.report]
    res = template_common.heatmap(
        [
            parts[m.x],
            parts[m.y],
        ],
        m,
        PKDict(
            x_label=field_label(m.x),
            y_label=field_label(m.y),
        ),
    )
    bunch = data.models.bunch
    res.summaryData = parts.summaryData
    return res


def _extract_report_data(data, run_dir):
    r = data.report
    m = re.split(r"(\d+)", r)
    f = getattr(pykern.pkinspect.this_module(), "_extract_report_" + m[0] if m else r)
    f = functools.partial(f, data, run_dir)
    if "Animation" in r:
        f = functools.partial(f, filename=_filename_for_report(run_dir, r))
    return f()


def _extract_report_elementAnimation(data, run_dir, filename):
    if _is_parameter_report_file(filename):
        return extract_parameter_report(data, run_dir, filename)
    m = data.models[data.report]
    t = madx_parser.parse_tfs_file(run_dir.join(filename), want_page=m.frameIndex)
    info = madx_parser.parse_tfs_page_info(run_dir.join(filename))[m.frameIndex]

    return template_common.heatmap(
        [to_floats(t[m.x]), to_floats(t[m.y1])],
        m,
        PKDict(
            x_label=field_label(m.x),
            y_label=field_label(m.y1),
            title="{}-{} at {}m, {} turn {}".format(
                m.x,
                m.y1,
                info.s,
                info.name,
                info.turn,
            ),
        ),
    )


def _extract_report_matchSummaryAnimation(data, run_dir, filename):
    return PKDict(
        summaryText=_parse_match_summary(run_dir, filename),
    )


def extract_report_twissFromParticlesAnimation(data, run_dir, filename):
    res = particle_beam.analyze_ptc_beam(
        particle_beam.read_ptc_data(run_dir.join(filename))[0],
        # TODO(pjm): should use the mass of the selected species
        mc2=SCHEMA.constants.particleMassAndCharge.proton[0],
    )
    # remap alpha/beta columns
    for dim in ("x", "y"):
        res[f"alf{dim}"] = res[f"alpha_{dim}"]
        del res[f"alpha_{dim}"]
        res[f"bet{dim}"] = res[f"beta_{dim}"]
        del res[f"beta_{dim}"]
    assert set(res.keys()) == set(
        PTC_OBSERVE_TWISS_COLS
    ), f"unknown ptc twiss columns={set(res.keys())} expected={PTC_OBSERVE_TWISS_COLS}"
    return extract_parameter_report(
        data,
        results=PKDict(res),
    )


def _extract_report_twissFromParticlesAnimation(data, run_dir, filename):
    return extract_report_twissFromParticlesAnimation(data, run_dir, filename)


def _extract_report_twissReport(data, run_dir):
    return extract_parameter_report(data, run_dir)


def _filename_for_report(run_dir, report):
    for info in _output_info(run_dir):
        if info.modelKey == report:
            return info.filename
    if report == "matchSummaryAnimation":
        return MADX_LOG_FILE
    raise AssertionError(f"no output file for report={report}")


def _format_field_value(state, model, field, el_type):
    v = model[field]
    if el_type == "Boolean" or el_type == "OptionalBoolean":
        v = "true" if v == "1" else "false"
    elif "LatticeBeamlineList" in el_type:
        v = state.id_map[int(v)].name
    elif el_type == "OutputFile":
        v = '"{}"'.format(
            state.filename_map[
                LatticeUtil.file_id(model._id, state.field_index)
            ].filename
        )
    elif el_type == "RPNValue":
        v = _format_rpn_value(v)
    return [field, v]


def _format_rpn_value(value):
    import astunparse
    import ast

    class Visitor(ast.NodeTransformer):
        def visit_Call(self, node):
            if node.func.id == "pow":
                return ast.BinOp(
                    left=node.args[0], op=ast.Pow(), right=node.args[1], keywords=[]
                )
            return node

    if code_variable.CodeVar.infix_to_postfix(value) == value:
        value = code_variable.PurePythonEval.postfix_to_infix(value)
    if type(value) == str and ("pow" in value or re.search(r"\-\s*\-", value)):
        tree = ast.parse(value)
        for n in ast.walk(tree):
            Visitor().visit(n)
            ast.fix_missing_locations(n)
        return astunparse.unparse(tree).strip().replace("**", "^")
    if type(value) == str and "-" in value and "^" in value:
        value = "(" + value + ")"
    return value


def _generate_commands(filename_map, util):
    _update_beam_energy(util.data)
    for c in util.data.models.commands:
        if c._type in (_PTC_TRACK_COMMAND, _PTC_TRACKLINE_COMMAND):
            c.onetable = "1"
        if (
            c._type == _PTC_TRACK_COMMAND
            and int(util.data.models.simulation.computeTwissFromParticles)
            and int(c.icase) == 4
        ):
            raise AssertionError(
                f"ptc_track.icase must be set to 5 or 6 to compute twiss from particles",
            )
    res = util.render_lattice(
        util.iterate_models(
            lattice.ElementIterator(filename_map, _format_field_value),
            "commands",
        ).result,
        want_semicolon=True,
        want_name=False,
    )
    return res


def _generate_lattice(filename_map, util):
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        want_semicolon=True,
        want_var_assign=True,
        madx_name=True,
    )


def _generate_variable(name, variables, visited):
    res = ""
    if name not in visited:
        res += "REAL {} = {};\n".format(name, _format_rpn_value(variables[name]))
        visited[name] = True
    return res


def _get_filename_for_element_id(file_id, data):
    return _build_filename_map(data)[file_id]


def _is_parameter_report_file(filename):
    return "twiss" in filename or "touschek" in filename


def _is_report(name, report):
    return name in report


def _iterate_and_format_rpns(data, schema):
    def _rpn_update(model, field):
        if code_variable.CodeVar.is_var_value(model[field]):
            model[field] = _format_rpn_value(model[field])

    lattice.LatticeUtil(data, schema).iterate_models(
        lattice.UpdateIterator(_rpn_update)
    )
    return data


def _output_info(run_dir):
    # cache outputInfo to file, used later for report frames
    info_file = run_dir.join(_OUTPUT_INFO_FILE)
    if os.path.isfile(str(info_file)):
        try:
            res = simulation_db.read_json(info_file)
            if not res or res[0].get("_version", "") == _OUTPUT_INFO_VERSION:
                return res
        except ValueError as e:
            pass
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    files = _build_filename_map(data)
    res = []
    for k in files.keys_in_order:
        f = files[k]
        if run_dir.join(f.filename).exists():
            res.append(file_info(f.filename, run_dir, k))
            if f.model_type == _PTC_TRACK_COMMAND and int(
                data.models.simulation.computeTwissFromParticles
            ):
                res.insert(
                    0,
                    PKDict(
                        modelKey="twissFromParticlesAnimation",
                        filename=f.filename,
                        isHistogram=False,
                        plottableColumns=PTC_OBSERVE_TWISS_COLS,
                        pageCount=0,
                    ),
                )
    if LatticeUtil.find_first_command(data, _END_MATCH_COMMAND):
        res.insert(
            0,
            PKDict(
                modelKey="matchAnimation",
                filename="madx.log",
                isHistogram=False,
                plottableColumns=[],
                pageCount=0,
            ),
        )
    if res:
        res[0]["_version"] = _OUTPUT_INFO_VERSION
    simulation_db.write_json(info_file, res)
    return res


def _parse_match_summary(run_dir, filename):
    path = run_dir.join(filename)
    node_names = ""
    res = ""
    with pkio.open_text(str(path)) as f:
        state = "search"
        for line in f:
            if re.search(r"^MATCH SUMMARY", line):
                state = "summary"
            elif state == "summary":
                if re.search(r"^END MATCH SUMMARY", line):
                    state = "node_names"
                else:
                    res += line
            elif state == "node_names":
                # MAD-X formats the outputs incorrectly when piped to a file
                # need to look after the END MATCH for node names
                # Global constraint:         dq1          4     0.00000000E+00    -3.04197881E-12     9.25363506E-24
                if (
                    len(line) > 28
                    and re.search(r"^\w.*?\:", line)
                    and line[26] == " "
                    and line[27] != " "
                ):
                    node_names += line
    if node_names:
        res = re.sub(r"(Node_Name .*?\n\-+\n)", r"\1" + node_names, res)
    return res


def _read_bunch_file(path, callback):
    with h5py.File(
        path,
        "r",
    ) as f:
        pp = pmd_beamphysics.readers.particle_paths(f)
        d = f[pp[-1]]
        if "beam" in d:
            d = d["beam"]
        # TODO(pjm): add to file validation
        if "position/x" not in d:
            raise AssertionError("OpenPMD file missing position/x dataset")
        return callback(d)


def _read_particles(h5):
    return PKDict(
        x=list(h5["position/x"]),
        y=list(h5["position/y"]),
        t=list(h5["position/t"]),
        px=list(h5["momentum/x"]),
        py=list(h5["momentum/y"]),
        pt=list(-numpy.array(h5["momentum/t"])),
    )


def _update_beam_energy(data):
    beam = LatticeUtil.find_first_command(data, "beam")
    assert beam, "BEAM missing from command list"
    bunch = data.models.bunch
    # TODO(pjm): file source needs to update beam mass, charge and energy
    if bunch.beamDefinition != "file":
        for e in SCHEMA.enum.BeamDefinition:
            if bunch.beamDefinition != e[0]:
                beam[e[0]] = 0
