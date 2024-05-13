"""Genesis execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import numpy
import os
import re
import sirepo.job
import sirepo.sim_data
import sirepo.simulation_db


# http://genesis.web.psi.ch/Manual/parameter.html
# In the docs the param is ITGAMGAUS. The code expect IGAMGAUS

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

GENESIS_INPUT_FILE = "genesis.in"
GENESIS_OUTPUT_FILE = "genesis.out"
_INPUT_VARIABLE_MODELS = (
    "electronBeam",
    "focusing",
    "io",
    "particleLoading",
    "mesh",
    "radiation",
    "scan",
    "simulationControl",
    "timeDependence",
    "undulator",
)

# POSIT: Same order as results in GENESIS_OUTPUT_FILE
_LATTICE_COLS = (
    "power",
    "increment",
    "p_mid",
    "phi_mid",
    "r_size",
    "energy",
    "bunching",
    "xrms",
    "yrms",
    "error",
)

_LATTICE_COL_LABEL = PKDict(
    xrms="rms x [m]",
    yrms="rms y [m]",
)

_LATTICE_DATA_FILENAME = "lattice{}.npy"

_LATTICE_RE = re.compile(r"\bpower\b[\s\w]+\n(.*?)(\n\n|$)", flags=re.DOTALL)
_MAGIN_PLOT_FIELD = "AW"
_FIELD_DISTRIBUTION_OUTPUT_FILENAME = GENESIS_OUTPUT_FILE + ".fld"
_PARTICLE_OUTPUT_FILENAME = GENESIS_OUTPUT_FILE + ".par"
_FINAL_FIELD_OUTPUT_FILENAME = GENESIS_OUTPUT_FILE + ".dfl"
_FINAL_PARTICLE_OUTPUT_FILENAME = GENESIS_OUTPUT_FILE + ".dpa"

_RUN_ERROR_RE = re.compile(r"(?:^\*\*\* )(.*error.*$)", flags=re.MULTILINE)

# POSIT: Same order as results in GENESIS_OUTPUT_FILE
_SLICE_COLS = (
    "z [m]",
    "aw",
    "qfld",
)

_SLICE_DATA_FILENAME = "slice.npy"

_SLICE_RE = re.compile(
    r"\s+z\[m\]\s+aw\s+qfld\s+\n(.*?)\n^\s*$\n\*",
    flags=re.DOTALL | re.MULTILINE,
)


_DATA_FILES = PKDict(
    particleAnimation=_PARTICLE_OUTPUT_FILENAME,
    fieldDistributionAnimation=_FIELD_DISTRIBUTION_OUTPUT_FILENAME,
    parameterAnimation=GENESIS_OUTPUT_FILE,
    finalParticleAnimation=_FINAL_PARTICLE_OUTPUT_FILENAME,
    finalFieldAnimation=_FINAL_FIELD_OUTPUT_FILENAME,
)


def background_percent_complete(report, run_dir, is_running):
    if is_running or (not os.path.exists(run_dir.join(GENESIS_OUTPUT_FILE))):
        return PKDict(percentComplete=0, frameCount=0)
    c = _get_frame_counts(run_dir)
    return PKDict(
        percentComplete=100,
        reports=[
            PKDict(
                modelName="fieldDistributionAnimation",
                frameCount=c.field,
            ),
            PKDict(
                modelName="finalParticleAnimation",
                frameCount=c.dpa,
            ),
            PKDict(
                modelName="finalFieldAnimation",
                frameCount=c.dfl,
            ),
            PKDict(
                modelName="parameterAnimation",
                frameCount=c.parameter,
            ),
            PKDict(
                modelName="particleAnimation",
                frameCount=c.particle,
            ),
        ],
    )


def genesis_success_exit(run_dir):
    dm = sirepo.simulation_db.read_json(
        run_dir.join(template_common.INPUT_BASE_NAME)
    ).models
    return (
        run_dir.join(GENESIS_OUTPUT_FILE).exists()
        and _LATTICE_RE.search(pkio.read_text(run_dir.join(GENESIS_OUTPUT_FILE)))
        and (
            dm.timeDependence.itdp == "1"
            or (
                run_dir.join(_FINAL_PARTICLE_OUTPUT_FILENAME).exists()
                and run_dir.join(_FINAL_PARTICLE_OUTPUT_FILENAME).size() > 0
                and not numpy.isnan(
                    numpy.fromfile(_FINAL_PARTICLE_OUTPUT_FILENAME, dtype=numpy.float64)
                ).any()
            )
        )
    )


def get_data_file(run_dir, model, frame, options):
    if res := _DATA_FILES.get(model):
        return res
    raise AssertionError(f"unknown model={model}")


def parse_genesis_error(run_dir):
    return "\n".join(
        [
            m.group(1).strip()
            for m in _RUN_ERROR_RE.finditer(
                pkio.read_text(run_dir.join(template_common.RUN_LOG))
            )
        ],
    )


def plot_magin(magin_filename):
    def _x_points(data):
        if data.unit_length == 1:
            return [x for x in range(len(data.points))]
        x = []
        c = 0
        for i in range(len(data.points)):
            x.append(str(c))
            c += float(data.unit_length)
        return x

    d = _parse_maginfile(
        _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_model_field("io", "maginfile", magin_filename)
        )
    )
    return template_common.parameter_plot(
        _x_points(d),
        [
            PKDict(
                points=d.points,
                label=f"{_MAGIN_PLOT_FIELD} Value",
            )
        ],
        PKDict(),
        PKDict(
            title="MAGINFILE",
            x_label="length (m)",
        ),
    )


def post_execution_processing(success_exit, run_dir, **kwargs):
    if success_exit:
        return None
    return parse_genesis_error(run_dir)


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def sim_frame_fieldDistributionAnimation(frame_args):
    n = frame_args.sim_in.models.mesh.ncar
    d = numpy.fromfile(
        str(frame_args.run_dir.join(_FIELD_DISTRIBUTION_OUTPUT_FILENAME)),
        dtype=numpy.float64,
    )
    # Divide by 2 to combine real and imaginary parts which are written separately
    s = int(d.shape[0] / (n * n) / 2)
    d = d.reshape(s, 2, n, n)
    # recombine as a complex number
    d = d[:, 0, :, :] + 1.0j * d[:, 1, :, :]
    return _field_plot(
        frame_args,
        d[int(frame_args.frameIndex), :, :],
    )


def sim_frame_parameterAnimation(frame_args):
    l, s = _get_lattice_and_slice_data(frame_args.run_dir, int(frame_args.frameIndex))
    x = _SLICE_COLS[0]
    plots = []
    for f in ("y1", "y2", "y3"):
        y = frame_args[f]
        if not y or y == "none":
            continue
        plots.append(
            PKDict(
                field=y,
                points=l[:, _LATTICE_COLS.index(y)].tolist(),
                label=_LATTICE_COL_LABEL.get(y, y),
            )
        )
    title = ""
    if frame_args.sim_in.models.timeDependence.itdp == "1":
        title = f"Slice {frame_args.frameIndex + 1}"
    return template_common.parameter_plot(
        s[:, _SLICE_COLS.index(x)].tolist(),
        plots,
        PKDict(),
        PKDict(
            title=title,
            x_label=x,
        ),
    )


def sim_frame_finalFieldAnimation(frame_args):
    n = frame_args.sim_in.models.mesh.ncar
    v = numpy.fromfile(
        str(frame_args.run_dir.join(_FINAL_FIELD_OUTPUT_FILENAME)), dtype=complex
    )
    v = v.reshape(
        int(len(v) / n / n),
        n,
        n,
    )
    return _field_plot(
        frame_args,
        v[frame_args.frameIndex],
    )


def sim_frame_finalParticleAnimation(frame_args):
    return _particle_plot(frame_args, _FINAL_PARTICLE_OUTPUT_FILENAME)


def sim_frame_particleAnimation(frame_args):
    return _particle_plot(frame_args, _PARTICLE_OUTPUT_FILENAME)


def stateful_compute_import_file(data, **kwargs):
    text = data.args.file_as_str
    if data.args.ext_lower != ".in":
        raise AssertionError(
            "invalid file={data.args.basename} extension, expecting .in",
        )
    res = sirepo.simulation_db.default_data(SIM_TYPE)
    res.models.simulation.name = data.args.purebasename
    return PKDict(imported_data=_parse_namelist(res, text))


def validate_file(file_type, path):
    if file_type == "io-partfile":
        if pkio.is_pure_text(path):
            return "The PARTFILE should be a binary file. Use the DISTFILE to import a text file."
    elif file_type == "io-distfile":
        if not pkio.is_pure_text(path):
            return "The DISTFILE should be a text file with columns: X PX Y PY T P."
    elif file_type == "io-maginfile":
        if not pkio.is_pure_text(path):
            return "The MAGINFILE should be a text file."
    return None


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(GENESIS_INPUT_FILE),
        _generate_parameters_file(data),
    )


def _field_plot(frame_args, d):
    if frame_args.fieldPlot == "phasePlot":
        d = numpy.arctan(d.imag / d.real)
    d = numpy.abs(d)
    s = d.shape[0]
    return PKDict(
        title=_z_title_at_frame(frame_args, frame_args.sim_in.models.io.ipradi),
        x_label="",
        x_range=[0, s, s],
        y_label="",
        y_range=[0, s, s],
        z_matrix=d.tolist(),
    )


def _get_col(col_key):
    # POSIT: ParticleColumn keys are in same order as columns in output
    for i, c in enumerate(SCHEMA.enum.ParticleColumn):
        if c[0] == col_key:
            return i, c[1]
    raise AssertionError(
        f"No column={SCHEMA.enum.ParticleColumn} with key={col_key}",
    )


def _generate_parameters_file(data):
    io = data.models.io
    io.outputfile = GENESIS_OUTPUT_FILE
    io.iphsty = 1
    io.ishsty = 1
    if data.models.timeDependence.itdp == "1":
        io.ippart = 0
        io.ipradi = 0
    else:
        io.idmppar = "1"
        io.idmpfld = "1"
    r = ""
    fmap = PKDict(
        wcoefz1="WCOEFZ(1)",
        wcoefz2="WCOEFZ(2)",
        wcoefz3="WCOEFZ(3)",
    )
    for m in _INPUT_VARIABLE_MODELS:
        for f, v in data.models[m].items():
            if f not in SCHEMA.model[m]:
                continue
            s = SCHEMA.model[m][f]
            if v == s[2] or str(v) == s[2]:
                continue
            if s[1] == "String":
                v = f"'{v}'"
            elif s[1] == "InputFile":
                if v:
                    v = f"'{_SIM_DATA.lib_file_name_with_model_field('io', f, v)}'"
                else:
                    continue
            r += f"{fmap.get(f, f.upper())} = {v}\n"
    if io.maginfile:
        r += "MAGIN = 1\n"
    return "\n".join(["$newrun", r, "$end\n"])


def _get_lattice_and_slice_data(run_dir, lattice_index):
    def _reshape_and_persist(data, cols, filename):
        d = data.reshape(int(data.size / len(cols)), len(cols))
        numpy.save(str(filename), d)
        return d

    f = run_dir.join(_LATTICE_DATA_FILENAME.format(lattice_index))
    if f.exists():
        return numpy.load(str(f)), numpy.load(str(run_dir.join(_SLICE_DATA_FILENAME)))
    o = pkio.read_text(run_dir.join(GENESIS_OUTPUT_FILE))
    c = 0
    for v in re.finditer(_LATTICE_RE, o):
        _reshape_and_persist(
            numpy.fromstring(v[1], sep="\t"),
            _LATTICE_COLS,
            run_dir.join(_LATTICE_DATA_FILENAME.format(c)),
        )
        c += 1
    return (
        numpy.load(str(f)),
        _reshape_and_persist(
            numpy.fromstring(_SLICE_RE.search(o)[1], sep="\t"),
            _SLICE_COLS,
            run_dir.join(_SLICE_DATA_FILENAME),
        ),
    )


def _get_frame_counts(run_dir):
    dm = sirepo.simulation_db.read_json(
        run_dir.join(template_common.INPUT_BASE_NAME)
    ).models
    n = dm.timeDependence.nslice if dm.timeDependence.itdp == "1" else 1
    res = PKDict(
        particle=0,
        field=0,
        parameter=n,
        dpa=n if run_dir.join(_FINAL_PARTICLE_OUTPUT_FILENAME).exists() else 0,
        dfl=n if run_dir.join(_FINAL_FIELD_OUTPUT_FILENAME).exists() else 0,
    )
    with pkio.open_text(run_dir.join(GENESIS_OUTPUT_FILE)) as f:
        for line in f:
            m = re.match("^\s*(\d+) (\w+): records in z", line)
            if m:
                res[m.group(2)] = int(m.group(1))
                if m.group(1) == "field":
                    break
    return res


def _parse_maginfile(filepath):
    if not pkio.is_pure_text(filepath):
        raise AssertionError(f"{filepath.basename} for maginfile should be text file")
    p = []
    u = 1
    with pkio.open_text(filepath) as f:
        for line in f:
            row = line.split()
            if row:
                if row[0] == _MAGIN_PLOT_FIELD:
                    p.append(row[1])
                if row[0] == "?" and "UNITLENGTH" in row[1]:
                    if row[2] == "=":
                        u = row[3]
                    else:
                        u = row[2]
    if p:
        return PKDict(unit_length=u, points=p)
    raise AssertionError(f"No AW fields present in maginfile={filepath.basename}")


def _parse_namelist(data, text):
    dm = data.models
    nls = template_common.NamelistParser().parse_text(text)
    if "newrun" not in nls:
        raise AssertionError('Missing "newrun" namelist')
    nl = nls["newrun"]

    if "wcoefz" in nl:
        nl["wcoefz1"] = nl["wcoefz"][0]
        nl["wcoefz2"] = nl["wcoefz"][1]
        nl["wcoefz3"] = nl["wcoefz"][2]
    missing_files = []
    for m in SCHEMA.model:
        for f in SCHEMA.model[m]:
            if f not in nl:
                continue
            v = nl[f]
            if isinstance(v, list):
                v = v[-1]
            t = SCHEMA.model[m][f][1]
            if t == "InputFile":
                if not _SIM_DATA.lib_file_exists(
                    _SIM_DATA.lib_file_name_with_model_field(m, f, v),
                ):
                    missing_files.append(
                        PKDict(
                            filename=v,
                            file_type="{}-{}".format(m, f),
                        )
                    )
                else:
                    dm.io[f] = v
            d = dm[m]
            if t == "Float":
                d[f] = float(v)
            elif t == "Integer":
                d[f] = int(v)
            elif t == "Boolean":
                d[f] = "1" if int(v) else "0"
            elif t == "ItGaus":
                d[f] = "1" if int(v) == 1 else "2" if int(v) == 2 else "3"
            elif t == "Lbc":
                d[f] = "0" if int(v) == 0 else "1"
            elif t == "Iertyp":
                v = int(v)
                if v < -2 or v > 2:
                    v = 0
                d[f] = str(v)
            elif t == "Iwityp":
                d[f] = "0" if int(v) == 0 else "1"
            elif t == "TaperModel":
                d[f] = "1" if int(v) == 1 else "2" if int(v) == 2 else "0"
    # TODO(pjm): remove this if scanning is implemented in the UI
    if missing_files:
        return PKDict(
            error="Missing data files",
            missingFiles=missing_files,
        )
    dm.scan.iscan = "0"
    return data


def _particle_plot(frame_args, filename):
    n = frame_args.sim_in.models.electronBeam.npart
    d = numpy.fromfile(str(frame_args.run_dir.join(filename)), dtype=numpy.float64)
    b = d.reshape(
        int(len(d) / len(SCHEMA.enum.ParticleColumn) / n),
        len(SCHEMA.enum.ParticleColumn),
        n,
    )
    x = _get_col(frame_args.x)
    y = _get_col(frame_args.y)
    return template_common.heatmap(
        [
            b[int(frame_args.frameIndex), x[0], :].tolist(),
            b[int(frame_args.frameIndex), y[0], :].tolist(),
        ],
        frame_args.sim_in.models.particleAnimation.pkupdate(frame_args),
        PKDict(
            title=_z_title_at_frame(frame_args, frame_args.sim_in.models.io.ippart),
            x_label=x[1],
            y_label=y[1],
        ),
    )


def _z_title_at_frame(frame_args, nth):
    s = _get_lattice_and_slice_data(frame_args.run_dir, 0)[1]
    if frame_args.frameReport in ("finalFieldAnimation", "finalParticleAnimation"):
        step = -1
    else:
        step = frame_args.frameIndex * nth
    z = s[:, 0][step]
    title = f"z: {z:.6f} [m]"
    if step >= 0:
        return f"{title} step: {step + 1}"
    if frame_args.sim_in.models.timeDependence.itdp == "1":
        title = f"Slice {frame_args.frameIndex + 1}, {title}"
    return title
