# -*- coding: utf-8 -*-
"""DeviceServer stand-in for controls

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo import simulation_db
from sirepo.sim_data.controls import AmpConverter
from sirepo.sim_data.controls import SimData
from sirepo.template import particle_beam
import copy
import flask
import http
import numpy
import os
import re
import sirepo.const
import sirepo.lib
import sirepo.template.madx


_PV_TO_ELEMENT_FIELD = PKDict(
    KICKER=PKDict(
        horizontal="hkick",
        vertical="vkick",
    ),
    HKICKER=PKDict(
        horizontal="kick",
    ),
    VKICKER=PKDict(
        vertical="kick",
    ),
    QUADRUPOLE=PKDict(
        none="k1",
    ),
)
_POSITION_PROP_NAME = "tbtOrbPositionM"
_READ_CURRENT_PROP_NAME = "readbackM"
_WRITE_CURRENT_PROP_NAME = "currentS"
_ARRAY_PROP_NAMES = set([_READ_CURRENT_PROP_NAME, _POSITION_PROP_NAME])
_SIM_OUTPUT_DIR = "DeviceServer"
_SET_CONTEXT = PKDict()

app = flask.Flask(__name__)


@app.route("/DeviceServer/api/device/context")
def device_context():
    res = pkio.random_base62(12)
    _SET_CONTEXT[res] = _query_params(["user", "procName", "procId", "machine"])
    return _http_response(res)


@app.route("/DeviceServer/api/device/list/value", methods=["PUT", "GET"])
def list_value():
    v = _query_params(["names", "props"])
    _assert_lengths(v, "names", "props")
    if flask.request.method == "GET":
        return _http_response(_read_values(v))
    v.update(_query_params(["values", "context"]))
    _assert_lengths(v, "names", "values")
    if v.context not in _SET_CONTEXT:
        _abort(
            f"set context: {v.context} not found in server state",
            http.HTTPStatus.PRECONDITION_FAILED.value,
        )
    return _http_response(_update_values(v))


@app.route("/")
def root():
    return "MAD-X DeviceServer stand-in\n"


def run(sim_id):
    app.config["sim"] = _load_sim("controls", simulation_db.assert_sid(sim_id))
    app.config["sim_dir"] = pkio.py_path(_SIM_OUTPUT_DIR)
    # prep for initial queries by running sim with no changes
    _init_sim()
    app.run()


def _abort(message, status=http.HTTPStatus.BAD_REQUEST.value):
    # TODO(pjm): set CAD-Error header
    # ex. CAD-Error: ado - no data to return
    # CAD-Error: Error adding entry :gov.bnl.cad.error.GenericModuleException: Metadata for currentX is not found.
    flask.abort(status, message)


def _assert_lengths(params, field1, field2):
    if len(params[field1]) != len(params[field2]):
        _abort(f"{field1} and {field2} must have the same length")


def _convert_amps_to_k(element, amps):
    amp_table = None
    if element.get("ampTable"):
        amp_table = app.config["sim"].models.ampTables[element.ampTable]
    return AmpConverter(
        app.config["sim"].models.command_beam,
        amp_table,
    ).current_to_kick(amps)


def _find_element(pv_name):
    pv = _find_process_variable(pv_name)
    for el in app.config["sim"].models.externalLattice.models.elements:
        if el._id == pv.elId:
            return pv, el
    _abort(f"processVariable is corrupt, no element for id: {pv}")


def _find_process_variable(pv_name):
    for pv in app.config["sim"].models.controlSettings.processVariables:
        name = re.sub(r"\[.*?\]$", "", pv.pvName)
        if pv_name == name:
            return pv
    _abort(f"unknown pv: {pv_name}")


def _format_prop_value(prop_name, value):
    if prop_name in _ARRAY_PROP_NAMES:
        # TODO(pjm): assumes the first value is the one which will be used
        return f"[{value} 0 0 0]"
    return value


def _http_response(content):
    res = flask.make_response(content)
    res.headers["sirepo-dev"] = "1"
    return res


def _init_sim():
    data = app.config["sim"]
    beam = data.models.command_beam
    bunch = data.models.bunch
    bunch.matchTwissParameters = "0"
    madx = data.models.externalLattice
    madx.models.command_beam = beam
    madx.models.bunch = bunch
    madx.models.simulation.computeTwissFromParticles = "1"
    fmap = PKDict(
        current_k1="k1",
        current_kick="kick",
        current_vkick="vkick",
        current_hkick="hkick",
    )
    for el in madx.models.elements:
        for f in [x for x in el if x in fmap]:
            el[fmap[f]] = _convert_amps_to_k(el, float(el[f]))
    _run_sim()


def _load_sim(sim_type, sim_id):
    return simulation_db.open_json_file(
        sim_type,
        path=simulation_db.user_path_root()
        .join(
            simulation_db.uid_from_dir_name(
                simulation_db.find_global_simulation(
                    "controls",
                    sim_id,
                    checked=True,
                ),
            )
        )
        .join(sim_type)
        .join(sim_id)
        .join(sirepo.const.SIM_DATA_BASENAME),
    )


def _position_from_twiss():
    path = app.config["sim_dir"].join("ptc_track.file.tfsone")
    if not path.exists():
        _abort(f"missing {path.basename} result file")
    beam_data, observes, columns = particle_beam.read_ptc_data(path)
    columns = particle_beam.analyze_ptc_beam(
        beam_data,
        mc2=0.938272046,
    )
    if not columns:
        _abort("simulation failed")
    for c in ("beta_x", "beta_y", "alpha_x", "alpha_y"):
        if list(filter(lambda x: numpy.isnan(x), columns[c])):
            _abort("twiss computation failed")
    monitors = PKDict()
    for el in app.config["sim"].models.externalLattice.models.elements:
        if el.type in ("MONITOR", "HMONITOR", "VMONITOR"):
            monitors[el.name] = el.type
    res = []
    for i in range(len(observes)):
        t = monitors.get(observes[i], "")
        if t == "MONITOR":
            res += [columns["x0"][i] * 1e6, columns["y0"][i] * 1e6]
        elif t == "HMONITOR":
            res += [columns["x0"][i] * 1e6]
        elif t == "VMONITOR":
            res += [columns["y0"][i] * 1e6]
    return res


def _query_params(fields):
    res = PKDict()
    for f in fields:
        if f not in flask.request.args:
            _abort(f"missing request argument: {f}")
        res[f] = flask.request.args[f]
        if f in ("names", "props", "values"):
            res[f] = re.split(r"\s*,\s*", res[f])
    return res


def _read_values(params):
    res = ""
    mon_count = 0
    positions = _position_from_twiss()
    for idx in range(len(params.names)):
        name = params.names[idx]
        prop = params.props[idx]
        pv, el = _find_element(f"{name}:{prop}")
        if res:
            res += " "
        if el.type in _PV_TO_ELEMENT_FIELD:
            if prop != _READ_CURRENT_PROP_NAME:
                _abort(f"read current pv must be {_READ_CURRENT_PROP_NAME} not {prop}")
            f = _PV_TO_ELEMENT_FIELD[el.type][pv.pvDimension]
            res += _format_prop_value(prop, el[SimData.current_field(f)])
        else:
            # must be a monitor, get value from twiss output file
            if prop != _POSITION_PROP_NAME:
                _abort(f"monitor position pv must be {_POSITION_PROP_NAME} not {prop}")
            res += _format_prop_value(prop, positions[mon_count])
            mon_count += 1
    return res


def _run_sim():
    outpath = app.config["sim_dir"]
    if not outpath.exists():
        pkio.mkdir_parent(outpath)
    d = sirepo.lib.SimData(
        copy.deepcopy(app.config["sim"].models.externalLattice),
        outpath.join("in.madx"),
        sirepo.template.madx.LibAdapter(),
    )
    d.write_files(outpath)
    with pkio.save_chdir(outpath):
        if os.system("madx in.madx > madx.log"):
            _abort(f"madx simulation failed, see {outpath}/madx.log")


def _update_values(params):
    for idx in range(len(params.names)):
        name = params.names[idx]
        prop = params.props[idx]
        value = params["values"][idx]
        pv, el = _find_element(f"{name}:{prop}")
        if prop != _WRITE_CURRENT_PROP_NAME:
            _abort(f"write current pv must be {_WRITE_CURRENT_PROP_NAME} not {prop}")
        f = _PV_TO_ELEMENT_FIELD[el.type][pv.pvDimension]
        if f not in el:
            _abort(f"unexpected field {f} for element type {el.type}")
        el[SimData.current_field(f)] = float(value)
        el[f] = _convert_amps_to_k(el, float(value))
    _run_sim()
    return ""
