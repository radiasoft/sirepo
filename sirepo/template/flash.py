"""FLASH execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import flash_parser
from sirepo.template import template_common
import base64
import numpy
import pygments
import pygments.formatters
import pygments.lexers
import re
import rsflash.plotting.extracts
import sirepo.const
import sirepo.mpi
import sirepo.sim_data
import zipfile

yt = None

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_GRID_EVOLUTION_FILE = "flash.dat"

_LINEOUTS_SAMPLING_SIZE = 256

_PLOT_FILE_PREFIX = "flash_hdf5_plt_cnt_"

# TODO(e-carlin): When katex for labels is implemented
# https://git.radiasoft.org/sirepo/issues/3384
# dens='$\frac{\mathrm{g}}{\mathrm{cm}^3}$'
# magz='B$_{\phi}$ [T]'
_PLOT_VARIABLE_LABELS = PKDict(
    dens="g/cm^3",
    depo="cm/s",
    fill="",
    flam="cms/s",
    kapa="",
    length="cm",
    magz="Bphi T",
    sumy="",
    tele="K",
    time="s",
    tion="K",
    trad="K",
    velx="cm/s",
    wall="",
    ye="",
)


def background_percent_complete(report, run_dir, is_running):
    def _grid_columns():
        c = _grid_evolution_columns(run_dir)
        return [x for x in c if x[0] != "#"] if c else None

    def _plot_filenames():
        return [
            PKDict(
                time=_time_and_units(yt.load(str(f)).parameters["time"]),
                filename=f.basename,
            )
            for f in files
        ]

    def _plot_vars():
        names = []
        if len(files):
            io = simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME),
            ).models.IO_IOMain
            idx = 1
            while io.get(f"plot_var_{idx}", ""):
                n = io[f"plot_var_{idx}"]
                if n != "none":
                    names.append(n)
                idx += 1
        return names

    res = PKDict(
        percentComplete=0 if is_running else 100,
    )
    if report == "setupAnimation":
        f = run_dir.join(_SIM_DATA.SETUP_PARAMS_SCHEMA_FILE)
        if f.exists():
            d = pkjson.load_any(pkio.read_text(f))
            res.pkupdate(
                frameCount=1,
                flashSchema=d.flashSchema,
                parValues=d.get("parValues"),
            )
    else:
        _init_yt()
        files = _h5_file_list(run_dir)
        if is_running and len(files):
            # the last file may be unfinished if the simulation is running
            files.pop()
        res.pkupdate(
            frameCount=len(files),
            plotVars=_plot_vars(),
            plotFiles=_plot_filenames(),
            gridEvolutionColumns=_grid_columns(),
        )
    return res


def get_data_file(run_dir, model, frame, options):
    n = None
    if model == "setupAnimation":
        if frame == SCHEMA.constants.setupLogFrameId:
            n = _SIM_DATA.SETUP_LOG
        elif frame == SCHEMA.constants.compileLogFrameId:
            n = _SIM_DATA.COMPILE_LOG
    if model == "animation":
        if frame == SCHEMA.constants.flashLogFrameId:
            # TODO(pjm): need constant in sirepo.mpi?
            n = sirepo.const.MPI_LOG
    if n:
        # TODO(pjm): client does not know which log files exists
        if not run_dir.join(n).exists():
            # TODO(robnagler) could this be "error=No file..." with reply_path?
            return template_common.JobCmdFile(
                reply_path=run_dir.join(n), reply_content="No file output available"
            )
        return template_common.text_data_file(n, run_dir)
    if model == "gridEvolutionAnimation":
        return _GRID_EVOLUTION_FILE
    if model == "oneDimensionProfileAnimation" or model == "varAnimation":
        return str(_h5_file_list(run_dir)[frame])
    raise AssertionError(f"unknown model={model} frame={frame}")


def post_execution_processing(success_exit, is_parallel, run_dir, **kwargs):
    if success_exit:
        return None
    e = None
    f = run_dir.join(sirepo.const.MPI_LOG)
    if f.exists():
        t = pkio.read_text(f)
        for r in (
            r"^\s*Error(?: message is|\:)\s*(.*?)\n",
            r"(Too many blocks.*?)\n",
        ):
            m = re.search(
                r,
                t,
                re.MULTILINE | re.DOTALL | re.IGNORECASE,
            )
            if m:
                e = m.group(1)
                break
    return e


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data, None)


def sim_frame_gridEvolutionAnimation(frame_args):
    c = _grid_evolution_columns(frame_args.run_dir)
    dat = numpy.loadtxt(str(frame_args.run_dir.join(_GRID_EVOLUTION_FILE)))
    stride = 20
    x = dat[::stride, 0]
    plots = []
    for v in "y1", "y2", "y3":
        n = frame_args[v]
        if n == "None":
            continue
        plots.append(
            {
                "name": n,
                "label": n,
                "points": dat[::stride, c.index(n)].tolist(),
            }
        )
    return {
        "title": "",
        "x_range": [min(x), max(x)],
        "y_label": "",
        "x_label": "time [s]",
        "x_points": x.tolist(),
        "plots": plots,
        "y_range": template_common.compute_plot_color_and_range(plots),
    }


def sim_frame_oneDimensionProfileAnimation(frame_args):
    def _files():
        if frame_args.selectedPlotFiles:
            return sorted(
                [
                    str(frame_args.run_dir.join(f))
                    for f in frame_args.selectedPlotFiles.split(",")
                ]
            )
        return [str(_h5_file_list(frame_args.run_dir)[-1])]

    _init_yt()
    plots = []
    x_points = []
    xs, ys, times = rsflash.plotting.extracts.get_lineouts(
        _files(),
        frame_args.var,
        frame_args.axis,
        _LINEOUTS_SAMPLING_SIZE,
        interpolate=str(frame_args.get("interpolate", "1")) == "1",
    )
    x = xs[0]
    r = [numpy.min(x), numpy.max(x)]
    for i, _ in enumerate(ys):
        plots.append(
            PKDict(
                name=i,
                label=_time_and_units(times[i]),
                points=ys[i].tolist(),
                x_points=xs[i].tolist(),
            )
        )
        m = numpy.min(xs[i])
        if m < r[0]:
            r[0] = m
        m = numpy.max(xs[i])
        if m > r[1]:
            r[1] = m
    return PKDict(
        plots=plots,
        title=frame_args.var,
        x_label=_PLOT_VARIABLE_LABELS.length,
        x_points=x.tolist(),
        x_range=r,
        y_label=_PLOT_VARIABLE_LABELS.get(frame_args.var, ""),
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def sim_frame_varAnimation(frame_args):
    def _amr_grid(all):
        if not int(frame_args.amrGrid):
            return None
        g = []
        for b, _ in all.blocks:
            g.append(
                [
                    [float(b.LeftEdge[0] / 100), float(b.RightEdge[0] / 100)],
                    [float(b.LeftEdge[1] / 100), float(b.RightEdge[1] / 100)],
                ]
            )
        return g

    _init_yt()
    from yt.visualization import plot_window
    from yt.visualization.fixed_resolution import FixedResolutionBuffer

    f = frame_args.var.lower()
    ds = yt.load(str(_h5_file_list(frame_args.run_dir)[frame_args.frameIndex]))
    axis = ["x", "y", "z"].index(frame_args.axis)
    (bounds, center, display_center) = plot_window.get_window_parameters(
        axis, "c", None, ds
    )
    slc = ds.slice(axis, center[axis], center=center)
    all = ds.all_data()
    dim = ds.domain_dimensions
    scale = 2**all.max_level
    if axis == 0:
        buff_size = (dim[1] * scale, dim[2] * scale)
    elif axis == 1:
        buff_size = (dim[0] * scale, dim[2] * scale)
    else:
        buff_size = (dim[0] * scale, dim[1] * scale)

    # TODO(pjm): antialis=True is important to get grid aligned?
    d = FixedResolutionBuffer(slc, bounds, buff_size, True)[f]

    l = PKDict(
        cartesian=PKDict(
            x=PKDict(x="y", y="z"),
            y=PKDict(x="z", y="x"),
            z=PKDict(x="x", y="y"),
        ),
        cylindrical=PKDict(
            r=PKDict(x="theta", y="z"),
            z=PKDict(x="r", y="theta"),
            theta=PKDict(x="r", y="z"),
        ),
        polar=PKDict(
            r=PKDict(x="phi", y="z"),
            phi=PKDict(x="r", y="z"),
            z=PKDict(x="r", y="phi"),
        ),
        spherical=PKDict(
            r=PKDict(x="theta", y="phi"),
            theta=PKDict(x="r", y="phi"),
            phi=PKDict(x="r", y="theta"),
        ),
    )

    g = frame_args.sim_in.models.Grid_GridMain.geometry
    aspect_ratio = buff_size[1] / buff_size[0]
    return PKDict(
        global_max=float(frame_args.vmax) if frame_args.vmax else None,
        global_min=float(frame_args.vmin) if frame_args.vmin else None,
        subtitle="Time: {}, Plot {}".format(
            _time_and_units(ds.parameters["time"]),
            frame_args.frameIndex + 1,
        ),
        title="{}".format(f),
        x_label=f"{l[g][frame_args.axis].x} [m]",
        x_range=[ds.parameters["xmin"] / 100, ds.parameters["xmax"] / 100, d.shape[1]],
        y_label=f"{l[g][frame_args.axis].y} [m]",
        y_range=[ds.parameters["ymin"] / 100, ds.parameters["ymax"] / 100, d.shape[0]],
        z_matrix=d.tolist(),
        amr_grid=_amr_grid(all),
        aspectRatio=aspect_ratio,
        summaryData=PKDict(
            aspectRatio=aspect_ratio,
        ),
    )


def sort_problem_files(files):
    def _sort_suffix(row):
        if row.name == "Config":
            return 1
        if row.name == _SIM_DATA.FLASH_PAR_FILE:
            return 2
        if re.search(r"\.f90", row.name, re.IGNORECASE):
            return 3
        return 4

    return sorted(files, key=lambda x: (_sort_suffix(x), x["name"]))


def stateful_compute_delete_archive_file(data, **kwargs):
    # TODO(pjm): python may have ZipFile.remove() method eventually
    pksubprocess.check_call_with_signals(
        [
            "zip",
            "-d",
            str(
                _SIM_DATA.lib_file_abspath(
                    _SIM_DATA.flash_app_lib_basename(data.args.simulationId),
                )
            ),
            data.args.filename,
        ]
    )
    return PKDict()


def stateful_compute_format_text_file(data, **kwargs):
    if data.args.filename == _SIM_DATA.FLASH_PAR_FILE and data.args.models.get(
        "flashSchema"
    ):
        text = _generate_par_file(PKDict(models=data.args.models))
    else:
        with zipfile.ZipFile(
            _SIM_DATA.lib_file_abspath(
                _SIM_DATA.flash_app_lib_basename(data.args.simulationId),
            )
        ) as f:
            text = f.read(data.args.filename)
    t = "text"
    if re.search(r"\.par$", data.args.filename, re.IGNORECASE):
        # works pretty well for par files
        t = "bash"
    elif re.search(r"\.f90", data.args.filename, re.IGNORECASE):
        t = "fortran"
    elif data.args.filename.lower() == "makefile":
        t = "makefile"
    return PKDict(
        html=pygments.highlight(
            text,
            pygments.lexers.get_lexer_by_name(t),
            pygments.formatters.HtmlFormatter(
                noclasses=True,
                linenos="inline" if t == "fortran" else False,
            ),
        ),
    )


def stateful_compute_get_archive_file(data, **kwargs):
    if data.args.filename == _SIM_DATA.FLASH_PAR_FILE and data.args.models.get(
        "flashSchema"
    ):
        r = pkcompat.to_bytes(_generate_par_file(PKDict(models=data.args.models)))
    else:
        with zipfile.ZipFile(
            _SIM_DATA.lib_file_abspath(
                _SIM_DATA.flash_app_lib_basename(data.args.simulationId),
            )
        ) as f:
            r = f.read(data.args.filename)
    return PKDict(
        encoded=pkcompat.from_bytes(base64.b64encode(r)),
    )


def stateful_compute_replace_file_in_zip(data, **kwargs):
    found = False
    for f in data.args.archiveFiles:
        if f.name == data.args.filename:
            found = True
    if found:
        stateful_compute_delete_archive_file(data)
    lib_file = _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_type(
            data.args.filename,
            "problemFile",
        ),
    )
    with zipfile.ZipFile(
        str(
            _SIM_DATA.lib_file_abspath(
                _SIM_DATA.flash_app_lib_basename(data.args.simulationId),
            )
        ),
        "a",
    ) as z:
        z.write(lib_file, data.args.filename)
    res = PKDict()
    if (
        data.args.filename == _SIM_DATA.FLASH_PAR_FILE
        and "flashSchema" in data.args.models
    ):
        res.parValues = flash_parser.ParameterParser().parse(
            data.args,
            pkio.read_text(lib_file),
        )
    lib_file.remove()
    if not found:
        data.args.archiveFiles.append(
            PKDict(
                name=data.args.filename,
            )
        )
        data.args.archiveFiles = sort_problem_files(data.args.archiveFiles)
    res.archiveFiles = data.args.archiveFiles
    return res


def stateful_compute_update_lib_file(data, **kwargs):
    c = _SIM_DATA.sim_db_client()
    t = c.uri(c.LIB_DIR, _SIM_DATA.flash_app_lib_basename(data.args.simulationId))
    if data.args.get("archiveLibId"):
        c.copy(
            c.uri(c.LIB_DIR, _SIM_DATA.flash_app_lib_basename(data.args.archiveLibId)),
            t,
        )
    else:
        c.move(
            c.uri(data.args.simulationId, _SIM_DATA.flash_app_archive_basename()),
            t,
        )
    return PKDict(archiveLibId=data.args.simulationId)


def stateless_compute_setup_command(data, **kwargs):
    return PKDict(
        setupCommand=" ".join(
            _SIM_DATA.flash_setup_command(data.args.setupArguments),
        )
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, run_dir),
    )
    if data.get("report") == "initZipReport":
        return
    return template_common.get_exec_parameters_cmd()


def _format_boolean(value, config=False):
    r = "TRUE" if value == "1" else "FALSE"
    if not config:
        # runtime parameters (par file) have dots before and after bool
        r = f".{r}."
    return r


def _generate_par_file(data):
    res = ""
    flash_schema = data.models.flashSchema
    for m in sorted(data.models):
        if m not in flash_schema.model:
            continue
        schema = flash_schema.model[m]
        heading = "# {}\n".format(flash_schema.view[m].title)
        has_heading = False
        for f in sorted(data.models[m]):
            if f not in schema:
                continue
            if f in (
                "basenm",
                "checkpointFileIntervalTime",
                "checkpointFileIntervalStep",
            ):
                # Simulation.basenm must remain the default
                # plotting routines depend on the constant name
                continue
            v = data.models[m][f]
            if v != schema[f][2]:
                if not has_heading:
                    has_heading = True
                    res += heading
                if schema[f][1] == "Boolean":
                    v = _format_boolean(v)
                res += '{} = "{}"\n'.format(f, v)
        if has_heading:
            res += "\n"
    return res


def _generate_parameters_file(data, run_dir):
    if data.get("report") == "initZipReport":
        return template_common.render_jinja(
            SIM_TYPE,
            PKDict(
                initialParFile=data.models.problemFiles.initialParFile,
                flashExampleName=data.models.problemFiles.flashExampleName,
                problemFileArchive=_SIM_DATA.flash_problem_files_archive_basename(data),
                appArchiveName=_SIM_DATA.flash_app_archive_basename(),
                simulationId=data.models.simulation.simulationId,
            ),
            "init-zip.py",
        )

    res = ""
    if data.get("report") != "setupAnimation":
        res = _generate_par_file(data)
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(
            exe_name=(
                run_dir.join(_SIM_DATA.flash_exe_basename(data)) if run_dir else ""
            ),
            is_setup_animation=data.get("report") == "setupAnimation",
            par=res,
            par_filename=_SIM_DATA.FLASH_PAR_FILE,
            mpi_cores=sirepo.mpi.cfg().cores,
        ),
    )


def _grid_evolution_columns(run_dir):
    try:
        with pkio.open_text(run_dir.join(_GRID_EVOLUTION_FILE)) as f:
            return [x for x in re.split("[ ]{2,}", f.readline().strip())]
    except FileNotFoundError:
        return []


def _h5_file_list(run_dir):
    return pkio.sorted_glob(run_dir.join("{}*".format(_PLOT_FILE_PREFIX)))


def _init_yt():
    global yt
    if yt:
        return
    import yt

    # 50 disables logging
    # https://yt-project.org/doc/reference/configuration.html#configuration-options-at-runtime
    yt.funcs.mylog.setLevel(50)


def _time_and_units(time):
    u = "s"
    if time < 1e-12:
        time *= 1e15
        u = "fs"
    elif time < 1e-9:
        time *= 1e12
        u = "ps"
    elif time < 1e-6:
        time *= 1e9
        u = "ns"
    elif time < 1e-3:
        time *= 1e6
        u = "µs"
    elif time < 1:
        time *= 1e3
        u = "ms"
    return f"{time:.2f} {u}"
