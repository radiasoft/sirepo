"""Common execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
from sirepo.template import code_variable
import math
import os
import re
import sirepo.const
import sirepo.sim_data
import sirepo.template
import sirepo.util
import subprocess
import sys
import types


DEFAULT_INTENSITY_DISTANCE = 20

#: Input json file
INPUT_BASE_NAME = sirepo.const.SIM_RUN_INPUT_BASENAME

#: Test if value is numeric text
NUMERIC_RE = re.compile(r"^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$")

#: Output json file
OUTPUT_BASE_NAME = "out"

#: Python file (not all simulations)
PARAMETERS_PYTHON_FILE = "parameters.py"

#: stderr and stdout
RUN_LOG = "run.log"

_HISTOGRAM_BINS_MAX = 500

_PLOT_LINE_COLOR = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


#: for JobCmdFile replies
_TEXT_SUFFIXES = (".py", ".txt", ".csv")


class JobCmdFile(PKDict):
    """Returned by dispatched job commands

    `analysis_job_dispatch`, `stateless_compute_dispatch`, and
    `stateful_compute_dispatch` support file returns.

    Args:
        reply_content (object): what to send [reply_path.read()]
        reply_path (py.path): py.path of file to read
        reply_uri (str): what to call the file [reply_path.basename]
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pksetdefault(error=None)
        if self.error:
            self.pksetdefault(state="error")
            return
        if not (self.get("reply_uri") or self.get("reply_path")):
            raise AssertionError(
                f"reply_uri or reply_path not in kwargs.keys={list(kwargs)}"
            )
        self.pksetdefault(
            reply_content=lambda: (
                pkcompat.to_bytes(pkio.read_text(self.reply_path))
                if self.reply_path.ext in _TEXT_SUFFIXES
                else self.reply_path.read_binary()
            ),
            reply_uri=lambda: self.reply_path.basename,
            state="ok",
        )


class LogParser(PKDict):
    def __init__(self, run_dir, **kwargs):
        super().__init__(run_dir=run_dir, **kwargs)
        self.pksetdefault(
            default_msg="An unknown error occurred",
            error_patterns=(r"Error: (.*)",),
            log_filename=RUN_LOG,
        )

    def parse_for_errors(self):
        p = self.run_dir.join(self.log_filename)
        if not p.exists() or p.size() <= 0:
            return ""
        res = ""
        e = set()
        with pkio.open_text(p) as f:
            for line in f:
                if m := self._parse_log_line(line):
                    if m not in e:
                        res += m
                        e.add(m)
        if res:
            return res
        return self.default_msg

    def _parse_log_line(self, line):
        res = ""
        for pattern in self.error_patterns:
            m = re.search(pattern, line)
            if m:
                res += m.group(1) + "\n"
        return res


class ModelUnits:
    """Convert model fields from native to sirepo format, or from sirepo to native format.

    Examples::
        def _xpas(value, is_native):
            # custom field conversion code would go here
            return value

        mu = ModelUnits({
            'CHANGREF': {
                'XCE': 'cm_to_m',
                'YCE': 'cm_to_m',
                'ALE': 'deg_to_rad',
                'XPAS': _xpas,
            },
        })
        m = mu.scale_from_native('CHANGREF', {
            'XCE': 2,
            'YCE': 0,
            'ALE': 8,
            'XPAS': '#20|20|20',
        })
        assert m['XCE'] == 2e-2
        assert ModelUnits.scale_value(2, 'cm_to_m', True) == 2e-2
        assert ModelUnits.scale_value(0.02, 'cm_to_m', False) == 2
    """

    # handler for common units, native --> sirepo scale
    _COMMON_HANDLERS = PKDict(
        cm_to_m=1e-2,
        mm_to_cm=1e-1,
        mrad_to_rad=1e-3,
        deg_to_rad=math.pi / 180,
    )

    def __init__(self, unit_def):
        """
        Args:
            unit_def (dict):
            Map of model name to field handlers
        """
        self.unit_def = unit_def

    def scale_from_native(self, name, model):
        """Scale values from native values into sirepo units."""
        return self.__scale_model(name, model, True)

    def scale_to_native(self, name, model):
        """Scale values from sirepo units to native values."""
        return self.__scale_model(name, model, False)

    @classmethod
    def scale_value(cls, value, scale_type, is_native):
        """Scale one value using the specified handler."""
        handler = cls._COMMON_HANDLERS.get(scale_type, scale_type)
        if isinstance(handler, float):
            return float(value) * (handler if is_native else 1 / handler)
        assert isinstance(handler, types.FunctionType), "Unknown unit scale: {}".format(
            handler
        )
        return handler(value, is_native)

    def __scale_model(self, name, model, is_native):
        if name in self.unit_def:
            for field in self.unit_def[name]:
                if field not in model:
                    continue
                model[field] = self.scale_value(
                    model[field], self.unit_def[name][field], is_native
                )
        return model


class _MPILogParser(LogParser):
    def parse_for_errors(self):
        p = self.run_dir.join(self.log_filename)
        e = None
        if p.exists():
            m = re.search(
                r"^Traceback .*?^\w*Error: (.*?)\n",
                pkio.read_text(p),
                re.MULTILINE | re.DOTALL,
            )
            if m:
                e = m.group(1)
        return e


class NamelistParser:
    def parse_text(self, text):
        import f90nml

        text = str(text.encode("ascii", "ignore"), "UTF-8")
        parser = f90nml.Parser()
        parser.global_start_index = 1
        return parser.reads(text)


class NoH5PathError(KeyError):
    """The given path into an h5 file does not exist"""

    pass


class ParticleEnergy:
    """Computes the energy related fields for a particle from one field.
    Units:
        mass [GeV/c^2]
        pc [GeV/c]
        energy [GeV]
        brho [Tm]
    """

    SPEED_OF_LIGHT = 299792458  # [m/s]

    ENERGY_PRIORITY = PKDict(
        impactx=["energy"],
        opal=["gamma", "energy", "pc"],
        madx=["energy", "pc", "gamma", "beta", "brho"],
    )

    # defaults unless constants.particleMassAndCharge is set in the schema
    PARTICLE_MASS_AND_CHARGE = PKDict(
        # mass [GeV]
        antiproton=[0.938272046, -1],
        electron=[5.10998928e-4, -1],
        muon=[0.1056583755, -1],
        positron=[5.10998928e-4, 1],
        proton=[0.938272046, 1],
    )

    @classmethod
    def compute_energy(cls, sim_type, particle, energy):
        p = PKDict(
            mass=cls.get_mass(sim_type, particle, energy),
            charge=cls.get_charge(sim_type, particle, energy),
        )
        for f in cls.ENERGY_PRIORITY[sim_type]:
            if f in energy and energy[f] != 0:
                v = energy[f]
                handler = "_ParticleEnergy__set_from_{}".format(f)
                getattr(cls, handler)(p, energy)
                energy[f] = v
                return energy
        assert False, "missing energy field: {}".format(energy)

    @classmethod
    def get_charge(cls, sim_type, particle, beam):
        return cls.__particle_info(sim_type, particle, beam)[1]

    @classmethod
    def get_mass(cls, sim_type, particle, beam):
        return cls.__particle_info(sim_type, particle, beam)[0]

    @classmethod
    def __particle_info(cls, sim_type, particle, beam):
        mass_and_charge = (
            sirepo.sim_data.get_class(sim_type)
            .schema()
            .constants.get(
                "particleMassAndCharge",
                cls.PARTICLE_MASS_AND_CHARGE,
            )
        )
        if particle in mass_and_charge:
            return mass_and_charge[particle]
        return [beam.mass, beam.charge]

    @classmethod
    def __set_from_beta(cls, particle, energy):
        assert (
            energy.beta >= 0 or energy.beta < 1
        ), "energy beta out of range: {}".format(energy.beta)
        energy.gamma = 1 / math.sqrt(1 - energy.beta**2)
        cls.__set_from_gamma(particle, energy)

    @classmethod
    def __set_from_brho(cls, particle, energy):
        energy.pc = energy.brho * abs(particle.charge) * cls.SPEED_OF_LIGHT * 1e-9
        cls.__set_from_pc(particle, energy)

    @classmethod
    def __set_from_energy(cls, particle, energy):
        energy.gamma = energy.energy / particle.mass
        cls.__set_from_gamma(particle, energy)

    @classmethod
    def __set_from_gamma(cls, particle, energy):
        assert energy.gamma >= 1, "energy gamma out of range: {}".format(energy.gamma)
        energy.energy = energy.gamma * particle.mass
        energy.kinetic_energy = energy.energy - particle.mass
        energy.beta = math.sqrt(1.0 - 1.0 / (energy.gamma**2))
        energy.pc = energy.gamma * energy.beta * particle.mass
        energy.brho = energy.pc / (abs(particle.charge) * cls.SPEED_OF_LIGHT * 1e-9)

    @classmethod
    def __set_from_pc(cls, particle, energy):
        r2 = energy.pc**2 / (particle.mass**2)
        energy.beta = math.sqrt(r2 / (1 + r2))
        cls.__set_from_beta(particle, energy)


def analysis_job_dispatch(data, **kwargs):
    t = sirepo.template.import_module(data.simulationType)
    return getattr(t, f"analysis_job_{_validate_method(t, data)}")(data, **kwargs)


def compute_field_range(args, compute_range, run_dir):
    """Computes the fieldRange values for all parameters across all animation files.
    Caches the value on the animation input file. compute_range() is called to
    read the simulation specific datafiles and extract the ranges by field.
    """
    from sirepo import simulation_db

    data = simulation_db.read_json(run_dir.join(INPUT_BASE_NAME))
    res = None
    n = args.modelName
    if n in data.models:
        if "fieldRange" in data.models[n]:
            res = data.models[n].fieldRange
        else:
            res = compute_range(run_dir)
            data.models[n].fieldRange = res
            simulation_db.write_json(run_dir.join(INPUT_BASE_NAME), data)
    return PKDict(fieldRange=res)


def compute_plot_color_and_range(plots, plot_colors=None, fixed_y_range=None):
    """For parameter plots, assign each plot a color and compute the full y_range.
    If a fixed range is provided, use that instead
    """
    y_range = fixed_y_range
    colors = plot_colors if plot_colors is not None else _PLOT_LINE_COLOR
    for i in range(len(plots)):
        plot = plots[i]
        plot["color"] = colors[i % len(colors)]
        if not plot["points"]:
            y_range = [0, 0]
        elif fixed_y_range is None:
            vmin = min(plot["points"])
            vmax = max(plot["points"])
            if y_range:
                if vmin < y_range[0]:
                    y_range[0] = vmin
                if vmax > y_range[1]:
                    y_range[1] = vmax
            else:
                y_range = [vmin, vmax]
    return y_range


def write_dict_to_h5(d, file_path, h5_path=None):
    """Store the contents of a dict in an h5 file starting at the provided path.
    Stores the data recursively so that
        {a: A, b: {c: C, d: D}}
    maps the data to paths
        <h5_path>/a   -> A
        <h5_path>/b/c -> C
        <h5_path>/b/d -> D

    h5_to_dict() performs the reverse process
    """
    import h5py

    if h5_path is None:
        h5_path = ""
    try:
        for i in range(len(d)):
            p = f"{h5_path}/{i}"
            try:
                with h5py.File(file_path, "a") as f:
                    f.create_dataset(p, data=d[i])
            except TypeError:
                write_dict_to_h5(d[i], file_path, h5_path=p)
    except KeyError:
        for k in d:
            p = f"{h5_path}/{k}"
            try:
                with h5py.File(file_path, "a") as f:
                    f.create_dataset(p, data=d[k])
            except TypeError:
                write_dict_to_h5(d[k], file_path, h5_path=p)


def enum_text(schema, name, value):
    for e in schema["enum"][name]:
        if e[0] == str(value):
            return e[1]
    assert False, "unknown {} enum value: {}".format(name, value)


def exec_parameters(path=None):
    from pykern import pkrunpy

    return pkrunpy.run_path_as_module(path or PARAMETERS_PYTHON_FILE)


def exec_parameters_with_mpi():
    from sirepo import mpi

    return mpi.run_script(pkio.read_text(PARAMETERS_PYTHON_FILE))


def file_extension_ok(file_path, white_list=None, black_list=["py", "pyc"]):
    """Determine whether a file has an acceptable extension

    Args:
        file_path (str): name of the file to examine
        white_list ([str]): list of file types allowed (defaults to empty list)
        black_list ([str]): list of file types rejected (defaults to
            ['py', 'pyc']). Ignored if white_list is not empty
    Returns:
        If file is a directory: True
        If white_list non-empty: True if the file's extension matches any in
        the list, otherwise False
        If white_list is empty: False if the file's extension matches any in
        black_list, otherwise True
    """
    if os.path.isdir(file_path):
        return True
    if white_list:
        in_list = False
        for ext in white_list:
            in_list = in_list or pkio.has_file_extension(file_path, ext)
        if not in_list:
            return False
        return True
    for ext in black_list:
        if pkio.has_file_extension(file_path, ext):
            return False
    return True


def flatten_data(d, res, prefix=""):
    """Takes a nested dictionary and converts it to a single level dictionary with
    flattened keys."""
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            flatten_data(v, res, prefix + k + "_")
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = v
    return res


def generate_parameters_file(data, is_run_mpi=False):
    from sirepo import mpi

    v = flatten_data(data["models"], PKDict())
    v.notes = _get_notes(v)
    v.mpi = mpi.abort_on_signal_code() if is_run_mpi else ""
    return render_jinja(None, v, name="common-header.py"), v


def get_exec_parameters_cmd(is_mpi=False):
    from sirepo import mpi

    return mpi.get_cmd() if is_mpi else (sys.executable, PARAMETERS_PYTHON_FILE)


def h5_to_dict(hf, path=None):
    d = PKDict()
    if path is None:
        path = "/"
    try:
        for k in hf[path]:
            try:
                d[k] = hf[path][k][()].tolist()
            except (AttributeError, TypeError):
                # AttributeErrors occur when invoking tolist() on non-arrays
                # TypeErrors occur when accessing a group with [()]
                # in each case we recurse one step deeper into the path
                p = "{}/{}".format(path, k)
                d[k] = h5_to_dict(hf, path=p)
    except TypeError:
        # this TypeError occurs when hf[path] is not iterable (e.g. a string)
        # assume this is a single-valued entry and run it through pkcompat
        return pkcompat.from_bytes(hf[path][()])
    except KeyError as e:
        # no such path into the h5 file - re-raise so we know where it came from
        raise NoH5PathError(e)

    # replace dicts with arrays on a 2nd pass
    try:
        indices = [int(k) for k in d.keys()]
        d_arr = [None] * len(indices)
        for i in indices:
            d_arr[i] = d[str(i)]
        d = d_arr
    except IndexError:
        # integer keys but not an array
        pass
    except ValueError:
        # keys not all integers, we're done
        pass
    return d


def heatmap(values, model, plot_fields=None, weights=None):
    """Computes a report histogram (x_range, y_range, z_matrix) for a report model."""
    import numpy

    r = None
    if "plotRangeType" in model:
        if model["plotRangeType"] == "fixed":
            r = [
                _plot_range(model, "horizontal"),
                _plot_range(model, "vertical"),
            ]
        elif model["plotRangeType"] == "fit" and "fieldRange" in model:
            r = [
                model.fieldRange[model["x"]],
                model.fieldRange[model["y"]],
            ]
    hist, edges = numpy.histogramdd(
        values,
        histogram_bins(model["histogramBins"]),
        weights=weights,
        range=r,
    )
    res = PKDict(
        x_range=[float(edges[0][0]), float(edges[0][-1]), len(hist)],
        y_range=[float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        z_matrix=hist.T.tolist(),
    )
    if plot_fields:
        res.update(plot_fields)
    return res


def histogram_bins(nbins):
    """Ensure the histogram count is in a valid range"""
    nbins = int(nbins)
    if nbins <= 0:
        nbins = 1
    elif nbins > _HISTOGRAM_BINS_MAX:
        nbins = _HISTOGRAM_BINS_MAX
    return nbins


def jinja_filename(filename):
    # append .jinja, because file may already have an extension
    return filename + ".jinja"


def model_from_frame_args(frame_args):
    if frame_args.frameReport in frame_args.sim_in.models:
        res = frame_args.sim_in.models[frame_args.frameReport]
        res.update(frame_args)
        return res
    return frame_args


def parameter_plot(x, plots, model, plot_fields=None, plot_colors=None):
    res = PKDict(
        x_points=x,
        x_range=[min(x), max(x)] if x else [0, 0],
        plots=plots,
        y_range=compute_plot_color_and_range(plots, plot_colors),
    )
    if "plotRangeType" in model:
        if model.plotRangeType == "fixed":
            res["x_range"] = _plot_range(model, "horizontal")
            res["y_range"] = _plot_range(model, "vertical")
        elif model.plotRangeType == "fit" and "fieldRange" in model:
            res["x_range"] = model.fieldRange[model.x]
            for i in range(len(plots)):
                r = model.fieldRange[plots[i]["field"]]
                if r[0] < res["y_range"][0]:
                    res["y_range"][0] = r[0]
                if r[1] > res["y_range"][1]:
                    res["y_range"][1] = r[1]
    if plot_fields:
        res.update(plot_fields)
    return res


def parse_enums(enum_schema):
    """Returns a list of enum values, keyed by enum name."""
    res = PKDict()
    for k in enum_schema:
        res[k] = PKDict()
        for v in enum_schema[k]:
            res[k][v[0]] = True
    return res


def parse_mpi_log(run_dir):
    return _MPILogParser(run_dir, log_filename=sirepo.const.MPI_LOG).parse_for_errors()


def read_dict_from_h5(file_path, h5_path=None):
    import h5py

    with h5py.File(file_path, "r") as f:
        return h5_to_dict(f, path=h5_path)


def read_last_csv_line(path):
    # for performance, don't read whole file if only last line is needed
    if not path.exists():
        return ""
    try:
        with open(str(path), "rb") as f:
            f.readline()
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b"\n":
                f.seek(-2, os.SEEK_CUR)
            return pkcompat.from_bytes(f.readline())
    except IOError:
        return ""


def read_sequential_result(run_dir):
    """Read result data file from simulation

    Args:
        run_dir (py.path): where to find output

    Returns:
        dict: result
    """
    from sirepo import simulation_db

    return simulation_db.read_json(
        simulation_db.json_filename(OUTPUT_BASE_NAME, run_dir),
    )


def render_jinja(sim_type, v, name=PARAMETERS_PYTHON_FILE, jinja_env=None):
    """Render the values into a jinja template.

    Args:
        sim_type (str): application name
        v: flattened model data
    Returns:
        str: source text
    """
    b = jinja_filename(name)
    return pkjinja.render_file(
        (
            sirepo.sim_data.get_class(sim_type).resource_path(b)
            if sim_type
            else sirepo.sim_data.resource_path(b)
        ),
        v,
        jinja_env=jinja_env,
    )


async def sim_frame(frame_id, op, qcall):
    f, s = sirepo.sim_data.parse_frame_id(frame_id)
    # document parsing the request
    qcall.parse_post(req_data=f, id=True, check_sim_exists=True)
    try:
        x = await op(f)
    except Exception as e:
        if isinstance(e, sirepo.util.ReplyExc):
            return e
        raise sirepo.util.UserAlert(
            "Report not generated",
            "exception={} str={} stack={}",
            type(e),
            e,
            pkdexc(),
        )
    r = qcall.reply_dict(x)
    if "error" not in x and s.want_browser_frame_cache(s.frameReport):
        return qcall.headers_for_cache(r)
    return qcall.headers_for_no_cache(r)


def sim_frame_dispatch(frame_args):
    from sirepo import simulation_db

    frame_args.pksetdefault(
        run_dir=lambda: simulation_db.simulation_run_dir(frame_args),
    ).pksetdefault(
        sim_in=lambda: simulation_db.read_json(
            frame_args.run_dir.join(INPUT_BASE_NAME),
        ),
    )
    t = sirepo.template.import_module(frame_args.simulationType)
    o = getattr(t, "sim_frame_" + frame_args.frameReport, None) or getattr(
        t, "sim_frame"
    )
    res = o(frame_args)
    if res is None:
        raise RuntimeError(
            "unsupported simulation_frame model={}".format(frame_args.frameReport)
        )
    return res


def stateful_compute_dispatch(data, **kwargs):
    t = sirepo.template.import_module(data.simulationType)
    m = _validate_method(t, data)
    k = PKDict(data=data)
    # TODO(robnagler) polymorphism needed; templates should be classes
    if re.search(r"(?:^rpn|_rpn)_", m):
        k.schema = getattr(t, "SCHEMA")
        t = getattr(t, "code_var")(data.variables)
    return getattr(t, f"stateful_compute_{m}")(**k, **kwargs)


def stateless_compute_dispatch(data, **kwargs):
    t = sirepo.template.import_module(data.simulationType)
    return getattr(
        t,
        f"stateless_compute_{_validate_method(t, data)}",
    )(data, **kwargs)


def subprocess_output(cmd, env=None):
    """Run cmd and return output or None, logging errors.

    Args:
        cmd (list): what to run
    Returns:
        str: output is None on error else a stripped string
    """
    err = None
    out = None
    try:
        p = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = p.communicate()
        if p.wait() != 0:
            raise subprocess.CalledProcessError(returncode=p.returncode, cmd=cmd)
    except subprocess.CalledProcessError as e:
        pkdlog("{}: exit={} err={}", cmd, e.returncode, err)
        return None
    if out:
        out = pkcompat.from_bytes(out)
        return out.strip()
    return ""


def text_data_file(filename, run_dir):
    """Return a datafile with a .txt extension so the text/plain mimetype is used."""
    return JobCmdFile(
        reply_path=run_dir.join(filename, abs=1),
        reply_uri=filename + ".txt",
    )


def validate_model(model_data, model_schema, enum_info):
    """Ensure the value is valid for the field type. Scales values as needed."""
    for k in model_schema:
        label = model_schema[k][0]
        field_type = model_schema[k][1]
        if k in model_data:
            value = model_data[k]
        elif len(model_schema[k]) > 2:
            value = model_schema[k][2]
        else:
            raise Exception(
                'no value for field "{}" and no default value in schema'.format(k)
            )
        if field_type in enum_info:
            if str(value) not in enum_info[field_type]:
                # Check a comma-delimited string against the enumeration
                for item in re.split(r"\s*,\s*", str(value)):
                    if item not in enum_info[field_type]:
                        assert (
                            item in enum_info[field_type]
                        ), '{}: invalid enum "{}" value for field "{}"'.format(
                            item, field_type, k
                        )
        elif field_type == "Float":
            if not value:
                value = 0
            v = float(value)
            if re.search(r"\[m(m|rad)]", label):
                v /= 1000
            elif re.search(r"\[n(m|rad)]", label) or re.search(r"\[nm/pixel\]", label):
                v /= 1e09
            elif re.search(r"\[ps]", label):
                v /= 1e12
            # TODO(pjm): need to handle unicode in label better (mu)
            elif re.search("\\[\xb5(m|rad)]", label) or re.search(r"\[mm-mrad]", label):
                v /= 1e6
            model_data[k] = float(v)
        elif field_type == "Integer":
            if not value:
                value = 0
            model_data[k] = int(value)
        elif value is None:
            # value is already None, do not convert
            pass
        else:
            model_data[k] = _escape(value)


def validate_models(model_data, model_schema):
    """Validate top-level models in the schema. Returns enum_info."""
    enum_info = parse_enums(model_schema["enum"])
    for k in model_data["models"]:
        if k in model_schema["model"]:
            validate_model(
                model_data["models"][k],
                model_schema["model"][k],
                enum_info,
            )
    if "beamline" in model_data["models"]:
        for m in model_data["models"]["beamline"]:
            validate_model(m, model_schema["model"][m["type"]], enum_info)
    return enum_info


def write_sequential_result(result, run_dir=None):
    """Write the results of a sequential simulation to disk.

    Args:
        result (dict): The results of the simulation
        run_dir (py.path): Defaults to current dir
    """
    from sirepo import simulation_db

    if not run_dir:
        run_dir = pkio.py_path()
    f = simulation_db.json_filename(OUTPUT_BASE_NAME, run_dir)
    assert not f.exists(), "{} file exists".format(OUTPUT_BASE_NAME)
    simulation_db.write_json(f, result)
    t = sirepo.template.import_module(
        simulation_db.read_json(
            simulation_db.json_filename(
                INPUT_BASE_NAME,
                run_dir,
            ),
        ),
    )
    if hasattr(t, "clean_run_dir"):
        t.clean_run_dir(run_dir)


def _escape(v):
    return re.sub(r"([^\\])[\"\']", r"\1", str(v))


def _get_notes(data):
    notes = []
    for key in data.keys():
        match = re.search(r"^(.+)_notes$", key)
        if match and data[key]:
            n_key = match.group(1)
            k = n_key[0].capitalize() + n_key[1:]
            k_words = [word for word in re.split(r"([A-Z][a-z]*)", k) if word != ""]
            notes.append((" ".join(k_words), data[key]))
    return sorted(notes, key=lambda n: n[0])


def _plot_range(report, axis):
    half_size = float(report["{}Size".format(axis)]) / 2.0
    midpoint = float(report["{}Offset".format(axis)])
    return [midpoint - half_size, midpoint + half_size]


def _validate_method(template, data):
    m = data.method
    assert re.search(
        r"^[a-z]\w{1,34}$",
        m,
        flags=re.IGNORECASE,
    ), f"method={m} invalid compute or analysis function"
    return m
