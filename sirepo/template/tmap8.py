"""tmap8 execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.template import code_variable
import pyhit
import re
import sirepo.sim_data

_BARE_FPARSE_RE = re.compile(r"^\$\{fparse\s+(?P<expr>.+)\}$")
_NESTED_FPARSE_UNIT_RE = re.compile(
    r"^\$\{units\s+\$\{fparse\s+(?P<expr>.+?)\}\s+(?P<unit>\S+?)(?:\s*->\s*\S+)?\s*\}$"
)
_UNIT_RE = re.compile(r"\$\{units\s+([0-9eE.+-]+)\s+(\S+?)(?:\s*->\s*\S+)?\s*\}")
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def stateful_compute_parse_parameters(data, **kwargs):
    p = _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_model_field(
            "simulationSettings", "inputFile", data.args.inputFile
        )
    )
    return PKDict(
        parameters=_extract_parameters(p),
    )


def validate_file(file_type, path, **kwargs):
    if file_type == "simulationSettings-inputFile":
        try:
            if not len(_extract_parameters(path)):
                return "TMAP8 input file contained no parameters"
        except RuntimeError as e:
            return "Failed to parse TMAP8 input file"


def _extract_parameters(path):
    """Return an ordered dict of top-level parameters in the input file at *path*.

    Each entry maps a parameter name to a dict with:
      - value: the numeric magnitude, or the bare `${fparse ...}` expression
        text (with the `${fparse` prefix and trailing `}` stripped) for
        derived parameters, or the raw value for non-unit string params
      - unit: the parameter's original (pre-conversion) unit, or None if unitless
    """
    r = []
    for name, raw_value in pyhit.load(str(path)).params():
        value, unit = raw_value, None
        if isinstance(raw_value, str):
            nested = _NESTED_FPARSE_UNIT_RE.match(raw_value)
            bare = None if nested else _BARE_FPARSE_RE.match(raw_value)
            if nested:
                value = nested.group("expr")
                unit = nested.group("unit")
            elif bare:
                value = bare.group("expr")
            else:
                match = _UNIT_RE.search(raw_value)
                if match:
                    magnitude, from_unit = match.groups()
                    value = float(magnitude)
                    unit = from_unit
        r.append(
            PKDict(
                name=name,
                value=value,
                defaultValue=value,
                unit=unit,
            )
        )
    return r
