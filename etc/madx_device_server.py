# -*- coding: utf-8 -*-
u"""DeviceServer stand-in for webcon/controls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo import simulation_db
from sirepo.sim_data.controls import AmpConverter
from sirepo.sim_data.controls import SimData
import copy
import flask
import http
import os
import re
import sirepo.lib
import sirepo.template.madx
import sirepo.template.madx_parser
import sys


_PV_TO_ELEMENT_FIELD = PKDict(
    KICKER=PKDict(
        horizontal='hkick',
        vertical='vkick',
    ),
    HKICKER=PKDict(
        horizontal='kick',
    ),
    VKICKER=PKDict(
        vertical='kick',
    ),
    QUADRUPOLE=PKDict(
        none='k1',
    ),
)
_POSITION_PROP_NAME = 'tbtOrbitPositionM'
_READ_CURRENT_PROP_NAME = 'readbackM'
_WRITE_CURRENT_PROP_NAME = 'currentS'
_ARRAY_PROP_NAMES = set([_READ_CURRENT_PROP_NAME, _POSITION_PROP_NAME])
_SIM_OUTPUT_DIR = 'DeviceServer'
_SET_CONTEXT = PKDict()

app = flask.Flask(__name__)


@app.route('/DeviceServer/api/device/context')
def device_context():
    res = pkio.random_base62(12)
    _SET_CONTEXT[res] = _query_params(['user', 'procName', 'procId', 'machine'])
    return res


@app.route('/DeviceServer/api/device/list/value', methods=['PUT', 'GET'])
def list_value():
    v = _query_params(['names', 'props'])
    _assert_lengths(v, 'names', 'props')
    if flask.request.method == 'GET':
        return _read_values(v)
    v.update(_query_params(['values', 'context']))
    _assert_lengths(v, 'names', 'values')
    if v.context not in _SET_CONTEXT:
        _abort(
            f'set context: {v.context} not found in server state',
            http.HTTPStatus.PRECONDITION_FAILED.value,
        )
    return _update_values(v)


@app.route('/')
def root():
    return 'MAD-X DeviceServer stand-in\n'


def _abort(message, status=http.HTTPStatus.BAD_REQUEST.value):
    #TODO(pjm): set CAD-Error header
    # ex. CAD-Error: ado - no data to return
    # CAD-Error: Error adding entry :gov.bnl.cad.error.GenericModuleException: Metadata for currentX is not found.
    flask.abort(status, message)


def _assert_lengths(params, field1, field2):
    if len(params[field1]) != len(params[field2]):
        _abort(f'{field1} and {field2} must have the same length')


def _convert_amps_to_k(element, amps):
    amp_table = None
    if element.get('ampTable'):
        amp_table = app.config['sim'].models.ampTables[element.ampTable]
    return AmpConverter(
        app.config['sim'].models.command_beam,
        amp_table,
    ).current_to_kick(amps)


def _find_element(pv_name):
    pv = _find_process_variable(pv_name)
    for el in app.config['sim'].models.externalLattice.models.elements:
        if el._id == pv.elId:
            return pv, el
    _abort(f'processVariable is corrupt, no element for id: {pv}')


def _find_process_variable(pv_name):
    for pv in app.config['sim'].models.controlSettings.processVariables:
        name = re.sub(r'\[.*?\]$', '', pv.pvName)
        if pv_name == name:
            return pv
    _abort(f'unknown pv: {pv_name}')


def _format_prop_value(prop_name, value):
    if prop_name in _ARRAY_PROP_NAMES:
        #TODO(pjm): assumes the first value is the one which will be used
        return f'[{value},0,0,0]'
    return value


def _load_sim(sim_type, sim_id):
    return simulation_db.open_json_file(
        sim_type,
        path=simulation_db.sim_data_file(
            sim_type,
            sim_id,
            simulation_db.uid_from_dir_name(
                simulation_db.find_global_simulation(
                    'controls',
                    sim_id,
                    checked=True,
                ),
            ),
        ),
    )


def _position_from_twiss_file(el, pv):
    path = app.config['sim_dir'].join('twiss.file.tfs')
    if not path.exists():
        _abort(f'missing {path.basename} result file')
    columns = sirepo.template.madx_parser.parse_tfs_file(str(path))
    for idx in range(len(columns.name)):
        name = columns.name[idx].replace('"', '')
        if name == el.name:
            if pv.pvDimension == 'horizontal':
                return columns.x[idx]
            if pv.pvDimension == 'vertical':
                return columns.y[idx]
            _abort(f'monitor {el.name} must have horizontal or vertical pvDimension')
    _abort(f'monitor {el.name} missing value in {path.basename} result file')


def _query_params(fields):
    res = PKDict()
    for f in fields:
        if f not in flask.request.args:
            _abort(f'missing request argument: {f}')
        res[f] = flask.request.args[f]
        if f in ('names', 'props', 'values'):
            res[f] = re.split(r'\s*,\s*', res[f])
    return res


def _read_values(params):
    res = ''
    for idx in range(len(params.names)):
        name = params.names[idx]
        prop = params.props[idx]
        pv, el = _find_element(f'{name}:{prop}')
        if res:
            res += ','
        if el.type in _PV_TO_ELEMENT_FIELD:
            if prop != _READ_CURRENT_PROP_NAME:
                _abort(f'read current pv must be {_READ_CURRENT_PROP_NAME} not {prop}')
            f = _PV_TO_ELEMENT_FIELD[el.type][pv.pvDimension]
            res += _format_prop_value(prop, el[SimData.current_field(f)])
        else:
            # must be a monitor, get value from twiss output file
            if prop != _POSITION_PROP_NAME:
                _abort(f'monitor position pv must be {_POSITION_PROP_NAME} not {prop}')
            res += _format_prop_value(prop, _position_from_twiss_file(el, pv))
    return res


def _run_sim():
    outpath = app.config['sim_dir']
    if not outpath.exists():
        pkio.mkdir_parent(outpath)
    d = sirepo.lib.SimData(
        copy.deepcopy(app.config['sim'].models.externalLattice),
        outpath.join('in.madx'),
        sirepo.template.madx.LibAdapter(),
    )
    d.write_files(outpath)
    with pkio.save_chdir(outpath):
        if os.system('madx in.madx > madx.log'):
            _abort(f'madx simulation failed, see {outpath}/madx.log')


def _update_values(params):
    for idx in range(len(params.names)):
        name = params.names[idx]
        prop = params.props[idx]
        value = params['values'][idx]
        pv, el = _find_element(f'{name}:{prop}')
        if prop != _WRITE_CURRENT_PROP_NAME:
            _abort(f'write current pv must be {_WRITE_CURRENT_PROP_NAME} not {prop}')
        f = _PV_TO_ELEMENT_FIELD[el.type][pv.pvDimension]
        if f not in el:
            _abort(f'unexpected field {f} for element type {el.type}')
        el[SimData.current_field(f)] = float(value)
        el[f] = _convert_amps_to_k(el, float(value))
    _run_sim()
    return ''


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise AssertionError(f'usage: {sys.argv[0]} <sim_id>')
    app.config['sim'] = _load_sim('controls', simulation_db.assert_sid(sys.argv[1]))
    app.config['sim_dir'] = pkio.py_path(_SIM_OUTPUT_DIR)
    # prep for initial queries by running sim with no changes
    _run_sim()
    app.run()
