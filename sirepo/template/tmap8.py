"""tmap8 execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.template import code_variable
from sirepo.template import template_common
import numpy
import pandas
import pyhit
import pykern.pkio
import re
import sirepo.sim_data
import sirepo.util

_BARE_FPARSE_RE = re.compile(r"^\$\{fparse\s+(?P<expr>.+)\}$")
_BARE_VAR_RE = re.compile(r"^\$\{(?P<var>[A-Za-z_]\w*)\}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")
_NESTED_FPARSE_UNIT_RE = re.compile(
    r"^\$\{units\s+\$\{fparse\s+(?P<expr>.+?)\}\s+(?P<unit>\S+?)(?:\s*->\s*(?P<convertUnit>\S+))?\s*\}$"
)
_NESTED_VAR_REF_RE = re.compile(r"\$\{([A-Za-z_]\w*)\}")
_UNIT_RE = re.compile(r"\$\{units\s+([0-9eE.+-]+)\s+(\S+?)(?:\s*->\s*(\S+))?\s*\}")
_MC_LOWER_PERCENTILE = 5
_MC_UPPER_PERCENTILE = 95
_MC_CI_LEVEL = _MC_UPPER_PERCENTILE - _MC_LOWER_PERCENTILE
_MC_SAMPLE_CSV_GLOB = "main_out_sub*_csv.csv"
_NONE = "None"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
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
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


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
    code_var(data.models.get("rpnVariables", [])).compute_cache(data, SCHEMA)
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(
        data, qcall, for_mc=bool(_uncertain_variables(data))
    )


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
    return template_common.parameter_plot(
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


def stateful_compute_parse_parameters(data, **kwargs):
    r = _extract_parameters(
        _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_model_field(
                "simulationSettings", "inputFile", data.args.inputFile
            )
        )
    )
    return PKDict(
        parameters=r, cache=code_var(r).compute_cache(PKDict(models=PKDict()), SCHEMA)
    )


def validate_file(file_type, path, **kwargs):
    if file_type == "simulationSettings-inputFile":
        try:
            if not len(_extract_parameters(path)):
                return "TMAP8 input file contained no parameters"
        except RuntimeError as e:
            return "Failed to parse TMAP8 input file"


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


def _extract_parameters(path):
    """Return an ordered dict of top-level TMAP8 parameters in the input file.

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
    """
    r = []
    root = pyhit.load(str(path))
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
            param_names=" ".join(v.name for v in uncertain_variables),
            seed=data.models.simulationSettings.seed,
        ),
        name=MC_MAIN_FILE,
    )


def _generate_parameters_file(data, qcall=None, for_mc=False):
    root = pyhit.load(
        str(
            _SIM_DATA.lib_file_abspath(
                _SIM_DATA.lib_file_name_with_model_field(
                    "simulationSettings",
                    "inputFile",
                    data.models.simulationSettings.inputFile,
                ),
                qcall=qcall,
            )
        )
    )
    for v in data.models.get("rpnVariables", []):
        if v.value != v.defaultValue:
            root[v.name] = _format_parameter_value(
                v.value, v.unit, v.get("convertUnit")
            )
    if for_mc:
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
                c["console"] = "false"
                if "csv" in c:
                    c.removeParam("csv")
                if not any(cc.name == "csv" for cc in c.children):
                    c.append("csv", type="CSV")
    return root.render()


def _mc_aggregate(csv_files):
    """Collect the per-sample CSVs from a Monte Carlo run into a single
    DataFrame of summary statistics vs. time: for every column except
    "time", adds "<column>_mean", "<column>_pNN", and "<column>_pNN"
    (lower/upper percentile) columns computed across all samples at each
    timestep, mirroring plot_uncertainty.py's aggregation approach.
    """
    frames = [pandas.read_csv(str(f)) for f in csv_files]
    res = PKDict(time=frames[0]["time"])
    for c in frames[0].columns:
        if c == "time":
            continue
        stack = numpy.vstack([f[c].to_numpy() for f in frames])
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


def _stat_report_file(run_dir):
    f = pykern.pkio.sorted_glob(run_dir.join("*.csv"))
    return f[0] if f else None


def _uncertain_variables(data):
    return [
        v
        for v in data.models.get("rpnVariables", [])
        if v.get("uncertaintyDistribution")
    ]


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
