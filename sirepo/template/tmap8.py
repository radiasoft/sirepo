"""tmap8 execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.template import code_variable
from sirepo.template import template_common
import pandas
import pyhit
import pykern.pkio
import re
import sirepo.sim_data

_BARE_FPARSE_RE = re.compile(r"^\$\{fparse\s+(?P<expr>.+)\}$")
_BARE_VAR_RE = re.compile(r"^\$\{(?P<var>[A-Za-z_]\w*)\}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_]\w*$")
_NESTED_FPARSE_UNIT_RE = re.compile(
    r"^\$\{units\s+\$\{fparse\s+(?P<expr>.+?)\}\s+(?P<unit>\S+?)(?:\s*->\s*(?P<convertUnit>\S+))?\s*\}$"
)
_UNIT_RE = re.compile(r"\$\{units\s+([0-9eE.+-]+)\s+(\S+?)(?:\s*->\s*(\S+))?\s*\}")
_NONE = "None"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
TMAP8_INPUT_FILE = "tmap8.i"


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=100,
        frameCount=0,
    )
    if is_running:
        return res
    f = _stat_report_file(run_dir)
    if not f:
        return res
    return res.pkupdate(
        frameCount=1,
        reports=[_report_info(f)],
    )


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.get("rpnVariables", [])).compute_cache(data, SCHEMA)
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data, qcall)


def sim_frame_plotAnimation(frame_args):
    d = pandas.read_csv(str(_stat_report_file(frame_args.run_dir)))
    if frame_args.x in ("", _NONE):
        frame_args.x = d.columns[0]
    units = frame_args.sim_in.models.simulationSettings.get("units", [])
    plots = PKDict()
    for f in ("x", "y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] in ("", _NONE):
            continue
        plots[f] = PKDict(
            label=_column_label(frame_args[f], units),
            dim=f,
            points=d[frame_args[f]].tolist(),
        )
    return template_common.parameter_plot(
        x=plots.x.points,
        plots=[p for p in plots.values() if p.dim != "x"],
        model=frame_args,
        plot_fields=PKDict(
            dynamicYLabel=True,
            title="",
            y_label="",
            x_label=plots.x.label,
        ),
    )


def stateful_compute_parse_parameters(data, **kwargs):
    p = _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_model_field(
            "simulationSettings", "inputFile", data.args.inputFile
        )
    )
    r = _extract_parameters(p)
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


def _extract_parameters(path):
    """Return an ordered dict of top-level parameters in the input file at *path*.

    Each entry maps a parameter name to a dict with:
      - value: the numeric magnitude, or the bare `${fparse ...}` expression
        text (with the `${fparse` prefix and trailing `}` stripped) for
        derived parameters, or the referenced variable name for a bare
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
                value = nested.group("expr")
                unit = nested.group("unit")
                convert_unit = nested.group("convertUnit")
            elif bare:
                value = bare.group("expr")
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


def _generate_parameters_file(data, qcall=None):
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
    return root.render()


def _report_info(csv_file):
    return PKDict(
        columns=[_NONE] + list(pandas.read_csv(str(csv_file), nrows=0).columns),
        name="TMAP8 Output",
        modelKey="plotAnimation",
        report="plotAnimation",
    )


def _stat_report_file(run_dir):
    f = pykern.pkio.sorted_glob(run_dir.join("*.csv"))
    return f[0] if f else None


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(TMAP8_INPUT_FILE),
        _generate_parameters_file(data),
    )
