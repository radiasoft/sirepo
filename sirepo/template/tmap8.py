"""tmap8 execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.template import code_variable
from sirepo.template import template_common
import base64
import binascii
import itertools
import numpy
import os.path
import pandas
import pyhit
import pykern.pkcompat
import pykern.pkio
import pykern.pkjson
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.util
import tempfile
import zipfile

_BARE_FPARSE_RE = re.compile(r"^\$\{fparse\s+(?P<expr>.+)\}$")
_BARE_VAR_RE = re.compile(r"^\$\{(?P<var>[A-Za-z_]\w*)\}$")
_COMMENT_LINE_RE = re.compile(r"^\s*#")
# unit names used in comments which aren't MOOSE unit names
_COMMENT_UNITS = frozenset(("Ci", "disintegrations", "microns", "molecules", "um"))
# counts and words which are only a unit in an expression, e.g. "at/m^3"
_COMMENT_UNITS_NOT_ALONE = frozenset(
    ("at", "atom", "atoms", "disintegrations", "in", "microns", "molecules")
)
# a comment word split into leading punctuation, the word, and trailing
_COMMENT_WORD_RE = re.compile(r"^([(\[{]*)(.*?)([)\]}.,;:]*)$")
# block parameters which name an input file read by TMAP8
_DATA_FILE_PARAMS = frozenset(("csv_file", "data_file", "file"))
_EXPERIMENTAL_COLOR = "#000000"
_EXPERIMENTAL_DATA_ERRORS = (KeyError, ValueError, zipfile.BadZipFile)
# strips "#", "=" and "-" decorations from a heading, e.g. "# ==== Geometry ===="
_HEADING_STRIP_RE = re.compile(r"^[\s#=-]+|[\s=-]+$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")
# ${units v a -> b} inside an expression, e.g. "${units E eV -> J} / kB"
_INNER_UNITS_RE = re.compile(
    r"\$\{units\s+(?P<value>[^\s{}]+)\s+(?P<unit>[^\s{}]+?)"
    + r"(?:\s*->\s*(?P<convert>[^\s{}]+))?\s*\}"
)
_INCLUDE_RE = re.compile(
    r"^(?P<prefix>\s*!include\s+)['\"]?(?P<path>[^'\"\s]+)['\"]?", re.MULTILINE
)
# POSIT: the models with InputFile fields in tmap8-schema.json
_LIB_FILE_PREFIXES = ("plotAnimation-", "simulationSettings-")
_NESTED_FPARSE_UNIT_RE = re.compile(
    r"^\$\{units\s+\$\{fparse\s+(?P<expr>.+?)\}\s+(?P<unit>\S+?)(?:\s*->\s*(?P<convertUnit>\S+))?\s*\}$"
)
_NESTED_VAR_REF_RE = re.compile(r"\$\{([A-Za-z_]\w*)\}")
_NUMBER_RE = re.compile(r"^[~+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")
_UNIT_RE = re.compile(r"\$\{units\s+([0-9eE.+-]+)\s+(\S+?)(?:\s*->\s*(\S+))?\s*\}")
# exponents of kg, m, s, A, K, mol, cd
_UNIT_DIMS = PKDict(
    current=(0, 0, 0, 1, 0, 0, 0),
    energy=(1, 2, -2, 0, 0, 0, 0),
    length=(0, 1, 0, 0, 0, 0, 0),
    mass=(1, 0, 0, 0, 0, 0, 0),
    none=(0, 0, 0, 0, 0, 0, 0),
    temperature=(0, 0, 0, 0, 1, 0, 0),
    time=(0, 0, 1, 0, 0, 0, 0),
)
# MOOSE unit names (as in ${units}), as (factor to SI, exponents of _UNIT_DIMS).
# POSIT: tests/tmap8_test.py checks these against MOOSE's own conversions.
_UNITS = PKDict(
    A=(1.0, _UNIT_DIMS.current),
    C=(1.0, (0, 0, 1, 1, 0, 0, 0)),
    Hz=(1.0, (0, 0, -1, 0, 0, 0, 0)),
    J=(1.0, _UNIT_DIMS.energy),
    K=(1.0, _UNIT_DIMS.temperature),
    N=(1.0, (1, 1, -2, 0, 0, 0, 0)),
    Pa=(1.0, (1, -1, -2, 0, 0, 0, 0)),
    V=(1.0, (1, 2, -3, -1, 0, 0, 0)),
    W=(1.0, (1, 2, -3, 0, 0, 0, 0)),
    # atoms, a count
    at=(1.0, _UNIT_DIMS.none),
    atom=(1.0, _UNIT_DIMS.none),
    atoms=(1.0, _UNIT_DIMS.none),
    cd=(1.0, (0, 0, 0, 0, 0, 0, 1)),
    day=(86400.0, _UNIT_DIMS.time),
    degC=(1.0, _UNIT_DIMS.temperature),
    eV=(1.602176634e-19, _UNIT_DIMS.energy),
    g=(1e-3, _UNIT_DIMS.mass),
    h=(3600.0, _UNIT_DIMS.time),
    m=(1.0, _UNIT_DIMS.length),
    min=(60.0, _UNIT_DIMS.time),
    mol=(1.0, (0, 0, 0, 0, 0, 1, 0)),
    s=(1.0, _UNIT_DIMS.time),
    year=(365.25 * 86400.0, _UNIT_DIMS.time),
)
# inch; "in" is a Python keyword, so it can't be a PKDict keyword argument
_UNITS["in"] = (0.0254, _UNIT_DIMS.length)
# added after scaling to SI: K = degC + 273.15; only for a unit on its own
_UNIT_OFFSETS = PKDict(degC=273.15)
# longest first, so "da" and "mu" match before "d" and "m"
_UNIT_PREFIXES = (
    ("da", 1e1),
    ("mu", 1e-6),
    ("Y", 1e24),
    ("Z", 1e21),
    ("E", 1e18),
    ("P", 1e15),
    ("T", 1e12),
    ("G", 1e9),
    ("M", 1e6),
    ("k", 1e3),
    ("h", 1e2),
    ("d", 1e-1),
    ("c", 1e-2),
    ("m", 1e-3),
    ("n", 1e-9),
    ("p", 1e-12),
    ("f", 1e-15),
    ("a", 1e-18),
    ("z", 1e-21),
    ("y", 1e-24),
)
# e.g. ^2, ^-3, ^0.5, ^(1/2)
_UNIT_EXPONENT_RE = re.compile(r"\^(\(-?\d+(?:\.\d+)?(?:/\d+)?\)|-?\d+(?:\.\d+)?)")
_UNIT_NAME_RE = re.compile(r"[A-Za-z]+")
_UNIT_TERM_RE = re.compile(r"(?P<sym>[A-Za-z]+|1)(?:\^\(?(?P<exp>-?\d+(?:\.\d+)?)\)?)?")
_MC_LOWER_PERCENTILE = 5
_MC_UPPER_PERCENTILE = 95
_MC_CI_LEVEL = _MC_UPPER_PERCENTILE - _MC_LOWER_PERCENTILE
_MC_SAMPLE_CSV_GLOB = "main_out_sub*_csv.csv"
_NONE = "None"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
# an unindented parameter assignment, i.e. a top-level parameter
_TOP_LEVEL_PARAM_RE = re.compile(r"^[A-Za-z_]\w*\s*=")
MC_MAIN_FILE = "main.i"
MC_SUB_FILE = "sub.i"
TMAP8_INPUT_FILE = "tmap8.i"


def background_percent_complete(report, run_dir, is_running):

    def _gather_results(res):
        r = _mc_report_info(_mc_sample_files(run_dir)) or _report_info(
            _stat_report_file(run_dir)
        )
        if r:
            res.pkupdate(
                frameCount=1,
                reports=[r],
            )
        return res

    def _mc_report_info(csv_files):
        if not csv_files:
            return None
        return _report_info(csv_files[0]).pkupdate(
            name="TMAP8 Output (Monte Carlo, {} samples)".format(len(csv_files)),
        )

    def _report_info(csv_file):
        if not csv_file:
            return None
        return PKDict(
            columns=[_NONE] + list(pandas.read_csv(str(csv_file), nrows=0).columns),
            name="TMAP8 Output",
            modelKey="plotAnimation",
            report="plotAnimation",
        )

    res = PKDict(
        percentComplete=100,
        frameCount=0,
    )
    if is_running:
        # TODO(pjm): percent complete or partial render of mc results
        return res
    return _gather_results(res)


def code_var(variables):
    return _CodeVar(variables, code_variable.PurePythonEval())


def get_data_file(run_dir, model, frame, options):
    if model == "plotAnimation":
        m = _mc_sample_files(run_dir)
        if not m:
            return _stat_report_file(run_dir)

        def _write(n):
            with sirepo.util.write_zip(str(n)) as z:
                for f in m:
                    z.write(str(f), f.basename)

        p = run_dir.join("tmap8_csv.zip")
        pykern.pkio.atomic_write(p, writer=_write)
        return p
    raise AssertionError(f"unknown model={model}")


def prepare_for_client(data, qcall, **kwargs):
    v = data.models.get("rpnVariables", [])
    if v and any("group" not in x for x in v):
        # simulations from prior versions have no group
        _add_parameter_groups(data, qcall)
    for x in v:
        # derived from comment and unit, so always current
        x.commentMath = _comment_math(x.get("comment"))
        x.unitMath = _unit_math(x.get("unit"))
    code_var(data.models.get("rpnVariables", [])).compute_cache(data, SCHEMA)
    return data


def python_source_for_model(data, model, qcall, for_export=False, **kwargs):
    u = _uncertain_variables(data)
    if u and for_export:
        # POSIT: same files as write_parameters, so main.i finds sub.i
        return PKDict(
            {
                MC_MAIN_FILE: _generate_monty_carlo_file(data, u),
                MC_SUB_FILE: _generate_parameters_file(data, qcall, for_mc=True),
            }
        )
    return _generate_parameters_file(data, qcall, for_mc=bool(u))


def sim_frame_plotAnimation(frame_args):
    m = _mc_sample_files(frame_args.run_dir)
    d = (
        _mc_aggregate(m)
        if m
        else pandas.read_csv(str(_stat_report_file(frame_args.run_dir)))
    )
    if frame_args.x in ("", _NONE):
        frame_args.x = "time" if "time" in d.columns else d.columns[0]
    units = frame_args.sim_in.models.simulationSettings.get("units", [])
    plots = []
    colors = []
    for f in ("y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] in ("", _NONE):
            continue
        color = template_common.PLOT_LINE_COLOR[
            len(colors) % len(template_common.PLOT_LINE_COLOR)
        ]
        p = _column_plots(frame_args[f], f, d, bool(m), units)
        plots += p
        colors += [color] * len(p)
    e = _experimental_plot(frame_args)
    if e:
        plots.append(e)
        colors.append(_EXPERIMENTAL_COLOR)
    res = template_common.parameter_plot(
        x=_x_points(d, frame_args.x, bool(m)),
        plots=plots,
        model=frame_args,
        plot_fields=PKDict(
            dynamicYLabel=True,
            title="",
            y_label="",
            x_label=_column_label(frame_args.x, units),
        ),
        plot_colors=colors,
    )
    if e:
        res.x_range = [
            min(res.x_range[0], min(e.x_points)),
            max(res.x_range[1], max(e.x_points)),
        ]
    return res


def stateful_compute_import_file(data, **kwargs):
    """Import a TMAP8 input file, requesting its includes and data files.

    The client re-posts the input file with ``arguments`` JSON
    ``{files: {basename: base64}}`` holding the files collected so far,
    until nothing is missing. The input is then merged into one file.
    """
    if data.args.ext_lower != ".i":
        raise sirepo.util.UserAlert(
            "Expecting a TMAP8 input file (.i)",
            "invalid ext={}",
            data.args.ext_lower,
        )
    f = _import_files(data.args)
    r = _merge_input(data.args.basename, f)
    if r.missing:
        return PKDict(importState="missingFiles", missingFiles=r.missing)
    d = PKDict()
    for n, k in _data_file_params(r.root):
        b = os.path.basename(n[k])
        if b not in d:
            d[b] = _lib_file_write_unique("dataFile", b, f[b])
        n[k] = d[b]
    t = r.root.render()
    p = _extract_parameters(r.root, _parameter_groups(t))
    if not p:
        raise sirepo.util.UserAlert(
            "TMAP8 input file contained no parameters",
            "no parameters file={}",
            data.args.basename,
        )
    res = sirepo.simulation_db.default_data(SIM_TYPE)
    res.models.simulation.name = data.args.purebasename
    res.models.simulationSettings = PKDict(
        dataFiles=list(d.values()),
        inputFile=_lib_file_write_unique("inputFile", data.args.basename, t),
    )
    res.models.rpnVariables = p
    res.models.rpnCache = code_var(p).compute_cache(PKDict(models=PKDict()), SCHEMA)
    return PKDict(imported_data=res)


def validate_file(file_type, path, **kwargs):
    if file_type == "plotAnimation-experimentalFile":
        try:
            _read_experimental_data(path)
        except _EXPERIMENTAL_DATA_ERRORS as e:
            return f"Failed to read experimental data: {e}"


class _CodeVar(code_variable.CodeVar):
    """Evaluates ${units} conversions as TMAP8 does

    Where a parameter is used by name, it has its converted value (see
    `_variables_for_eval`). A parameter's own expression is evaluated as
    written, in its own unit, like its value field. The client looks up an
    expression's computed value by its text.
    """

    def __init__(self, variables, evaluator):
        super().__init__(_variables_for_eval(variables), evaluator)
        self._source_variables = variables

    def compute_cache(self, data, schema):
        res = super().compute_cache(data, schema)
        if res is None:
            return res
        # POSIT: same key and value as recompute_cache: eval_var of the text
        for v in self._source_variables:
            x = v.get("value")
            if isinstance(x, str) and self.is_var_value(x):
                r, err = self.eval_var(x)
                if not err:
                    res[self.canonicalize(x)] = r
        return res

    def eval_var(self, expr):
        return super().eval_var(_expand_units(expr) if isinstance(expr, str) else expr)


def _add_parameter_groups(data, qcall):
    """Set group on parameters which don't have it"""
    n = data.models.get("simulationSettings", PKDict()).get("inputFile")
    if not n:
        return
    b = _SIM_DATA.lib_file_name_with_model_field("simulationSettings", "inputFile", n)
    if not _SIM_DATA.lib_file_exists(b, qcall=qcall):
        return
    t = pykern.pkio.read_text(_input_file(n, qcall=qcall))
    p = PKDict(
        (x.name, x) for x in _extract_parameters(pyhit.parse(t), _parameter_groups(t))
    )
    for v in data.models.rpnVariables:
        x = p.get(v.name)
        v.setdefault("group", x.group if x else "")


def _column_label(name, units):
    for u in units:
        if u.name == name:
            return "{} (${}$)".format(name, u.unit) if u.unit else name
    return name


def _column_plots(col, dim, d, is_mc, units):
    """Return the plot dict(s) for one selected y-column.

    In a Monte Carlo run, if *col* has aggregated stats, returns a shaded
    confidence-band dict (dashed behind the mean) plus a mean-line dict --
    both get the same color from the caller so they read as one legend
    series. Otherwise returns a single line dict.
    """
    if is_mc and "{}_mean".format(col) in d.columns:
        lo = d["{}_p{:02d}".format(col, _MC_LOWER_PERCENTILE)].tolist()
        hi = d["{}_p{:02d}".format(col, _MC_UPPER_PERCENTILE)].tolist()
        return [
            PKDict(
                label="{} ({}% CI)".format(_column_label(col, units), _MC_CI_LEVEL),
                dim=dim,
                style="band",
                points=hi,
                pointsLower=lo,
                pointsUpper=hi,
                opacity=0.25,
            ),
            PKDict(
                label=_column_label(col, units),
                dim=dim,
                points=d["{}_mean".format(col)].tolist(),
            ),
        ]
    return [
        PKDict(
            label=_column_label(col, units),
            dim=dim,
            points=d[col].tolist(),
        )
    ]


def _comment_math(comment):
    """The comment with its units as math, for mathRendering

    A word is a unit when it parses as a unit expression (`_unit_latex`).
    A single unit name, which could be an ordinary word, is a unit only
    when it is the whole comment, is in parentheses, follows a number or
    "in", or starts the comment before "-" or "=".

    Returns:
        str: text with $latex$ units, or "" if there are none or the
            comment has a "$", e.g. ${units ...}
    """

    def _is_alone_unit(name, words, index, lead, trail):
        if name in _COMMENT_UNITS_NOT_ALONE:
            return False
        if len(words) == 1 or ("(" in lead and ")" in trail):
            return True
        p = words[index - 1].lstrip("([{") if index else ""
        if _NUMBER_RE.match(p) or p == "in":
            return True
        return index == 0 and words[1] in ("-", "=")

    if not comment:
        return ""
    t = re.split(r"(\s+)", comment)
    w = [x for x in t if x and not x.isspace()]
    i = -1
    f = False
    r = []
    for x in t:
        if not x or x.isspace():
            r.append(x)
            continue
        i += 1
        if "$" in x:
            # mathRendering would see math in it, e.g. ${units ...}
            return ""
        l, c, e = _COMMENT_WORD_RE.match(x).groups()
        # keep the parentheses of an expression, e.g. "W/(mum*K)"
        while e.startswith(")") and c.count("(") > c.count(")"):
            c += ")"
            e = e[1:]
        u = _unit_latex(c)
        if u and (u.is_expression or _is_alone_unit(c, w, i, l, e)):
            f = True
            r.append(f"{l}${u.latex}${e}")
        else:
            r.append(x)
    return "".join(r) if f else ""


def _data_file_params(root):
    """Yield (node, name) for block parameters naming a relative input file"""
    for n in root.descendants:
        for k, v in n.params():
            if (
                k in _DATA_FILE_PARAMS
                and isinstance(v, str)
                and "${" not in v
                and not os.path.isabs(v)
            ):
                yield n, k


def _expand_units(expr):
    """Replace each ${units v a -> b} in expr with v converted to b

    ${units v a} (no conversion) is v. An unknown unit is left as is, so
    the expression can't be evaluated.
    """

    def _replace(match):
        if not match.group("convert"):
            return "(" + match.group("value") + ")"
        c = _unit_conversion(match.group("unit"), match.group("convert"))
        if not c:
            return match.group(0)
        return _scaled(match.group("value"), c)

    return _INNER_UNITS_RE.sub(_replace, expr)


def _experimental_plot(frame_args):
    """Scatter plot of the experimental data file, or None"""
    if not frame_args.get("experimentalFile"):
        return None
    d = _read_experimental_data(
        _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_model_field(
                "plotAnimation", "experimentalFile", frame_args.experimentalFile
            )
        )
    )
    return PKDict(
        circleRadius=3,
        dim="experimental",
        label=frame_args.get("experimentalLabel") or "Experiment",
        points=(
            d.y * float(frame_args.experimentalYScale)
            + float(frame_args.experimentalYOffset)
        ).tolist(),
        style="scatter",
        x_points=(
            d.x * float(frame_args.experimentalXScale)
            + float(frame_args.experimentalXOffset)
        ).tolist(),
    )


def _extract_parameters(root, groups):
    """Return an ordered list of top-level TMAP8 parameters in the input tree.

    Args:
        root (pyhit.Node): input tree
        groups (dict): parameter name to group heading, from `_parameter_groups`

    Each entry maps a parameter name to a dict with:
      - value: the numeric magnitude, or the bare `${fparse ...}` expression
        text (with the `${fparse` prefix and trailing `}` stripped, and any
        nested `${varname}` references reduced to bare `varname`, since
        `${...}` isn't valid syntax for the RPN/python expression evaluator)
        for derived parameters, or the referenced variable name for a bare
        `${varname}` expression, or the raw value for non-unit string params
      - unit: the parameter's original (pre-conversion) unit, or None if unitless
      - convertUnit: the `-> unit` conversion target, or None if not converted
      - comment: the trailing `# ...` comment text for the parameter, or None
      - group: the heading of the block of parameters it's in, or ""
    """
    r = []
    for name, raw_value in root.params():
        value, unit, convert_unit = raw_value, None, None
        if isinstance(raw_value, str):
            nested = _NESTED_FPARSE_UNIT_RE.match(raw_value)
            bare = None if nested else _BARE_FPARSE_RE.match(raw_value)
            bare_var = None if (nested or bare) else _BARE_VAR_RE.match(raw_value)
            if nested:
                value = _NESTED_VAR_REF_RE.sub(r"\1", nested.group("expr"))
                unit = nested.group("unit")
                convert_unit = nested.group("convertUnit")
            elif bare:
                value = _NESTED_VAR_REF_RE.sub(r"\1", bare.group("expr"))
            elif bare_var:
                value = bare_var.group("var")
            else:
                match = _UNIT_RE.search(raw_value)
                if match:
                    magnitude, from_unit, to_unit = match.groups()
                    value = float(magnitude)
                    unit = from_unit
                    convert_unit = to_unit
        r.append(
            PKDict(
                name=name,
                value=value,
                defaultValue=value,
                unit=unit,
                convertUnit=convert_unit,
                comment=root.comment(name),
                group=groups.get(name, ""),
            )
        )
    return r


def _format_parameter_value(value, unit, convert_unit=None):
    """Reconstruct the `${...}` (or plain) text for *value*/*unit*, inverting `_extract_parameters`."""
    if isinstance(value, str):
        expr = (
            "${{{}}}".format(value)
            if _IDENTIFIER_RE.match(value)
            else "${{fparse {}}}".format(value)
        )
    else:
        expr = str(value)
    if not unit:
        return expr
    u = "{} -> {}".format(unit, convert_unit) if convert_unit else unit
    return "${{units {} {}}}".format(expr, u)


def _generate_monty_carlo_file(data, uncertain_variables):
    """Generate a MOOSE Stochastic Tools main.i driver for the parameters file"""
    n = ["{}_dist".format(v.name) for v in uncertain_variables]
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(
            sub_file=MC_SUB_FILE,
            distributions=[
                PKDict(
                    name=n,
                    type=v.uncertaintyDistribution,
                    fields=list((v.get("uncertainty") or {}).items()),
                )
                for n, v in zip(n, uncertain_variables)
            ],
            dist_names=" ".join(n),
            num_rows=data.models.simulationSettings.numSamples,
            param_names=" ".join(_sampled_name(v) for v in uncertain_variables),
            seed=data.models.simulationSettings.seed,
        ),
        name=MC_MAIN_FILE,
    )


def _generate_parameters_file(data, qcall=None, for_mc=False):
    root = pyhit.load(
        str(_input_file(data.models.simulationSettings.inputFile, qcall=qcall))
    )
    d = set(data.models.simulationSettings.get("dataFiles", []))
    for n, k in _data_file_params(root):
        # POSIT: stateful_compute_import_file set these to the dataFiles names.
        # Like elegant, refer to the lib file, which is in run_dir and exports.
        if n[k] in d:
            n[k] = _SIM_DATA.lib_file_name_with_model_field(
                "simulationSettings", "dataFile", n[k]
            )
    for v in data.models.get("rpnVariables", []):
        if v.value != v.defaultValue:
            root[v.name] = _format_parameter_value(
                v.value, v.unit, v.get("convertUnit")
            )
    if for_mc:
        for v in _uncertain_variables(data):
            if v.get("convertUnit"):
                # MultiAppSamplerControl replaces the whole parameter, which
                # would skip the unit conversion, so sample a plain value in
                # the original unit and convert it here
                root[_sampled_name(v)] = _format_parameter_value(v.value, None)
                root[v.name] = _format_parameter_value(
                    _sampled_name(v), v.unit, v.convertUnit
                )
        d = {"console"}
        for c in root.children:
            if c.name == "Executioner":
                # MultiApps/[sub]'s ignore_solve_not_converge (see
                # _generate_monty_carlo_file) requires this, or MOOSE errors
                # at startup: "Requesting to ignore failed solutions, but
                # 'Executioner/error_on_dtmin' is true in sub-application."
                c["error_on_dtmin"] = "false"
            elif c.name == "Outputs":
                # batch MC runs solve hundreds of times over -- disable
                # expensive/noisy outputs, and use a named [csv] block
                # (not the bare "csv = true" flag) so that
                # SamplerFullSolveMultiApp names each sample's file
                # main_out_sub<N>_csv.csv, matching _MC_SAMPLE_CSV_GLOB
                if "exodus" in c:
                    c["exodus"] = "false"
                    d.add("exodus")
                for cc in c.children:
                    if cc.get("type") == "Exodus":
                        d.add(cc.name)
                        cc.remove()
                # MOOSE rejects file_base with multiple sub-app instances
                for n in [c] + c.children:
                    if "file_base" in n:
                        n.removeParam("file_base")
                c["console"] = "false"
                if "csv" in c:
                    c.removeParam("csv")
                if not any(cc.name == "csv" for cc in c.children):
                    c.append("csv", type="CSV")
        # objects may name the disabled outputs, e.g. outputs = 'console csv'
        # outputs = '' means all outputs, so only rewrite when one is removed
        for n in root.descendants:
            if "outputs" in n:
                o = n["outputs"].split()
                k = [x for x in o if x not in d]
                if len(k) < len(o):
                    n["outputs"] = " ".join(k) or "none"
    return root.render()


def _import_files(args):
    """Files for an import: the input file and those the client sent

    Returns:
        PKDict: basename to bytes
    """
    res = PKDict()
    a = args.get("import_file_arguments")
    if a:
        try:
            for k, v in pykern.pkjson.load_any(a).files.items():
                res[os.path.basename(k)] = base64.b64decode(v)
        except (binascii.Error, KeyError, ValueError) as e:
            raise sirepo.util.UserAlert(
                "Invalid import file arguments", "arguments error={}", e
            )
    res[args.basename] = pykern.pkcompat.to_bytes(args.file_as_str)
    return res


def _include_names(text):
    return [os.path.basename(m.group("path")) for m in _INCLUDE_RE.finditer(text)]


def _input_file(name, qcall=None):
    return _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_model_field(
            "simulationSettings", "inputFile", name
        ),
        qcall=qcall,
    )


def _lib_file_write_unique(field, name, content):
    """Write a simulationSettings lib file, returning its stored name.

    The lib directory is shared by all of the user's simulations. A
    same-named file with the same content is reused; one with different
    content is left alone and this is stored as ``<pure>-<n><ext>``.
    """
    c = pykern.pkcompat.to_bytes(content)
    p, e = os.path.splitext(name)
    for i in itertools.count(1):
        n = name if i == 1 else f"{p}-{i}{e}"
        b = _SIM_DATA.lib_file_name_with_model_field("simulationSettings", field, n)
        if not _SIM_DATA.lib_file_exists(b):
            _SIM_DATA.lib_file_write(b, c)
            return n
        if _SIM_DATA.lib_file_abspath(b).read_binary() == c:
            return n


def _mc_aggregate(csv_files):
    """Collect the per-sample CSVs from a Monte Carlo run into a single
    DataFrame of summary statistics vs. time: for every column except
    "time", adds "<column>_mean", "<column>_pNN", and "<column>_pNN"
    (lower/upper percentile) columns computed across all samples at each
    timestep, mirroring plot_uncertainty.py's aggregation approach.

    Samples with adaptive time stepping have different timesteps, so
    each sample is interpolated onto the first sample's times.
    """
    frames = [pandas.read_csv(str(f)) for f in csv_files]
    res = PKDict(time=frames[0]["time"])
    for c in frames[0].columns:
        if c == "time":
            continue
        stack = numpy.vstack([numpy.interp(res.time, f["time"], f[c]) for f in frames])
        res["{}_mean".format(c)] = stack.mean(axis=0)
        res["{}_p{:02d}".format(c, _MC_LOWER_PERCENTILE)] = numpy.percentile(
            stack, _MC_LOWER_PERCENTILE, axis=0
        )
        res["{}_p{:02d}".format(c, _MC_UPPER_PERCENTILE)] = numpy.percentile(
            stack, _MC_UPPER_PERCENTILE, axis=0
        )
    return pandas.DataFrame(res)


def _mc_sample_files(run_dir):
    return pykern.pkio.sorted_glob(run_dir.join(_MC_SAMPLE_CSV_GLOB))


def _merge_input(input_file, files):
    """Load input_file with its includes from files.

    Follows ``!include`` recursively, then, once all includes are
    present, the block parameters in `_DATA_FILE_PARAMS`. The files are
    copied into a temporary directory by basename, with each
    ``!include`` path reduced to its basename.

    Args:
        input_file (str): basename of the main input
        files (PKDict): basename to bytes
    Returns:
        PKDict: missing (basenames) and, if none are missing, root
    """

    def _text(name):
        try:
            return pykern.pkcompat.from_bytes(files[name])
        except UnicodeDecodeError:
            raise sirepo.util.UserAlert(
                f"File {name} is not a text file", "decode failed name={}", name
            )

    def _includes():
        res = []
        m = []

        def _scan(name):
            for n in _include_names(_text(name)):
                if n == input_file or n in res or n in m:
                    continue
                if n in files:
                    res.append(n)
                    _scan(n)
                else:
                    m.append(n)

        _scan(input_file)
        return res, m

    i, m = _includes()
    if m:
        return PKDict(missing=m)
    with tempfile.TemporaryDirectory() as d:
        d = pykern.pkio.py_path(d)
        for n in [input_file] + i:
            pykern.pkio.write_text(
                d.join(n),
                _INCLUDE_RE.sub(
                    lambda x: x.group("prefix") + os.path.basename(x.group("path")),
                    _text(n),
                ),
            )
        try:
            r = pyhit.load(str(d.join(input_file)))
        except RuntimeError as e:
            raise sirepo.util.UserAlert(
                "Failed to parse TMAP8 input file", "pyhit error={}", e
            )
    m = []
    for n, k in _data_file_params(r):
        b = os.path.basename(n[k])
        if b not in files and b not in m:
            m.append(b)
    return PKDict(missing=m, root=r)


def _parameter_groups(text):
    """Group heading for each top-level parameter.

    A comment block directly above a top-level parameter is a heading,
    named by its first line. A parameter belongs to the nearest heading
    above it. A comment block followed by a blank line or a block, such
    as a file's opening comments, isn't a heading.

    Returns:
        PKDict: parameter name to heading, "" when there is none
    """
    l = text.splitlines()
    h = []
    c = ""
    i = 0
    while i < len(l):
        if not _COMMENT_LINE_RE.match(l[i]):
            h.append(c)
            i += 1
            continue
        j = i
        while j + 1 < len(l) and _COMMENT_LINE_RE.match(l[j + 1]):
            j += 1
        if j + 1 < len(l) and _TOP_LEVEL_PARAM_RE.match(l[j + 1]):
            c = _HEADING_STRIP_RE.sub("", l[i])
        h.extend([c] * (j + 1 - i))
        i = j + 1
    r = pyhit.parse(text)
    return PKDict((k, h[r.line(k) - 1]) for k, _ in r.params())


def _read_experimental_data(path):
    """Read the first two columns of a .csv or .xlsx file.

    A header row, or any other row which isn't numeric, is skipped.

    Returns:
        PKDict: x and y numpy arrays
    """
    if path.ext.lower() == ".xlsx":
        d = pandas.read_excel(str(path), header=None)
    else:
        for s in (",", "\t", r"\s+"):
            d = pandas.read_csv(
                str(path),
                encoding="utf-8-sig",
                header=None,
                sep=s,
                skipinitialspace=True,
            )
            if len(d.columns) >= 2:
                break
    if len(d.columns) < 2:
        raise ValueError("expecting two columns")
    d = d.iloc[:, :2].apply(pandas.to_numeric, errors="coerce").dropna()
    if not len(d):
        raise ValueError("no numeric rows")
    return PKDict(x=d.iloc[:, 0].to_numpy(), y=d.iloc[:, 1].to_numpy())


def _sampled_name(variable):
    """Parameter name the Monte Carlo sampler sets for an uncertain variable"""
    return variable.name + "_sampled" if variable.get("convertUnit") else variable.name


def _scaled(value, conversion):
    """Expression for value (number or expression text) * scale + offset"""
    s, o = conversion
    return "(({}) * {!r}{})".format(value, s, " + {!r}".format(o) if o else "")


def _stat_report_file(run_dir):
    """The TMAP8 output csv, ignoring lib files in run_dir

    Lib files are linked into run_dir, or downloaded there after the
    run (e.g. a new experimental file), so they are excluded by prefix.
    """
    f = [
        p
        for p in pykern.pkio.sorted_glob(run_dir.join("*.csv"))
        if not p.basename.startswith(_LIB_FILE_PREFIXES)
    ]
    return f[0] if f else None


def _uncertain_variables(data):
    return [
        v
        for v in data.models.get("rpnVariables", [])
        if v.get("uncertaintyDistribution")
    ]


def _unit_conversion(unit, convert_unit):
    """How to convert a value from unit to convert_unit

    Returns:
        tuple: (scale, offset), value_to = value * scale + offset, or None if
            a unit is unknown or the dimensions differ
    """
    a = _unit_si(unit)
    b = _unit_si(convert_unit)
    if not a or not b or any(abs(x - y) > 1e-9 for x, y in zip(a[1], b[1])):
        return None
    return (
        a[0] / b[0],
        (_UNIT_OFFSETS.get(unit, 0.0) - _UNIT_OFFSETS.get(convert_unit, 0.0)) / b[0],
    )


def _unit_latex(text):
    """LaTeX for a unit expression such as "W/(mum*K)" or "mol/sqrt(Pa)"

    expr := term (("/" | "*") term)*
    term := ("sqrt(" expr ")" | "(" expr ")" | name | "1") ("^" exponent)?

    Returns:
        PKDict: latex, and is_expression (has an operator or exponent),
            or None if text isn't a unit expression of known names
    """

    class _Invalid(Exception):
        pass

    def _exponent():
        m = _UNIT_EXPONENT_RE.match(text, s.i)
        if not m:
            return ""
        s.i = m.end()
        s.is_expression = True
        return "^{" + m.group(1).strip("()") + "}"

    def _expr():
        r = _term()
        while s.i < len(text) and text[s.i] in "/*":
            r += "/" if text[s.i] == "/" else r" \cdot "
            s.i += 1
            s.is_expression = True
            r += _term()
        return r

    def _group(open_text):
        s.i += len(open_text)
        r = _expr()
        if not text.startswith(")", s.i):
            raise _Invalid()
        s.i += 1
        return f"({r})" if open_text == "(" else r"\sqrt{" + r + "}"

    def _name(name):
        if name == "um":
            return r"\mu\mathrm{m}"
        if name in _UNITS or name in _COMMENT_UNITS:
            return r"\mathrm{" + name + "}"
        for p, _ in _UNIT_PREFIXES:
            b = name[len(p) :]
            if name.startswith(p) and b in _UNITS and b not in _UNIT_OFFSETS:
                return (r"\mu\mathrm{" + b if p == "mu" else r"\mathrm{" + name) + "}"
        raise _Invalid()

    def _term():
        if text.startswith("sqrt(", s.i):
            s.is_expression = True
            r = _group("sqrt(")
        elif text.startswith("(", s.i):
            r = _group("(")
        elif text.startswith("1/", s.i):
            s.i += 1
            r = "1"
        else:
            m = _UNIT_NAME_RE.match(text, s.i)
            if not m:
                raise _Invalid()
            s.i = m.end()
            r = _name(m.group())
        return r + _exponent()

    s = PKDict(i=0, is_expression=False)
    try:
        l = _expr()
    except _Invalid:
        return None
    if s.i != len(text):
        return None
    return PKDict(latex=l, is_expression=s.is_expression)


def _unit_math(unit):
    """The unit as $latex$, for mathRendering, or "" if not understood"""
    u = _unit_latex(unit) if unit else None
    return f"${u.latex}$" if u else ""


def _unit_si(unit):
    """(factor to SI, exponents) for a unit such as "m^4/at/s", or None"""

    def _symbol(name):
        if name in _UNITS:
            return _UNITS[name]
        for p, f in _UNIT_PREFIXES:
            b = name[len(p) :]
            if name.startswith(p) and b in _UNITS and b not in _UNIT_OFFSETS:
                return (f * _UNITS[b][0], _UNITS[b][1])
        return None

    t = re.split(r"\s*([*/])\s*", unit.strip())
    f = 1.0
    d = [0.0] * len(_UNIT_DIMS.none)
    for o, x in zip(["*"] + t[1::2], t[0::2]):
        m = _UNIT_TERM_RE.fullmatch(x)
        if not m:
            return None
        if m.group("sym") == "1":
            continue
        u = _symbol(m.group("sym"))
        if not u:
            return None
        e = float(m.group("exp") or 1) * (1 if o == "*" else -1)
        f *= u[0] ** e
        d = [a + b * e for a, b in zip(d, u[1])]
    return (f, tuple(d))


def _variables_for_eval(variables):
    """Values as TMAP8 sees them, for evaluating expressions

    ${units} inside a value is converted, and a top-level ${units v a -> b}
    parameter is in b, since TMAP8 substitutes the converted value where
    other parameters use it.
    """
    res = []
    for v in variables:
        x = v.get("value")
        if isinstance(x, str):
            x = _expand_units(x)
        c = (
            _unit_conversion(v.get("unit"), v.get("convertUnit"))
            if v.get("unit") and v.get("convertUnit")
            else None
        )
        if c:
            x = x * c[0] + c[1] if isinstance(x, (int, float)) else _scaled(x, c)
        res.append(PKDict(v).pkupdate(value=x))
    return res


def _x_points(d, x, is_mc):
    # in a Monte Carlo run, only "time" survives _mc_aggregate() unsuffixed --
    # every other column only exists as <x>_mean/_p05/_p95, so use the mean
    # for the x-axis (a confidence band doesn't make sense for the x-axis)
    if is_mc and "{}_mean".format(x) in d.columns:
        return d["{}_mean".format(x)].tolist()
    return d[x].tolist()


def write_parameters(data, run_dir, is_parallel):
    u = _uncertain_variables(data)
    if u:
        pykern.pkio.write_text(
            run_dir.join(MC_SUB_FILE),
            _generate_parameters_file(data, for_mc=True),
        )
        pykern.pkio.write_text(
            run_dir.join(MC_MAIN_FILE),
            _generate_monty_carlo_file(data, u),
        )
    else:
        pykern.pkio.write_text(
            run_dir.join(TMAP8_INPUT_FILE),
            _generate_parameters_file(data),
        )
