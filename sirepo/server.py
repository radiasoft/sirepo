# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from subprocess import Popen, PIPE
import datetime
import json
import os
import random
import re
import shutil
import string

from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
import flask
import numconv
import py
import sirepo.srw_template


#: Known emporary directory where simulation dirs are created
_WORK_DIR = None

#: Where simulation config files are found
_SIMULATION_DIR = None

#: Cache of examples (list(json))
_SRW_EXAMPLES = None

#: Where server files and static files are found
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

#: Which values need to be downscaled (1/1000)
_SCALE_VALUES = [
    'period',
    'horizontalPosition',
    'verticalPosition',
    'horizontalApertureSize',
    'verticalApertureSize',
    'horizontalRange',
    'verticalRange',
]

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Verify ID
_ID_RE = re.compile('^[{}]{{{}}}$'.format(_ID_CHARS, _ID_LEN))

#: Is file name json
_JSON_FILE_RE = re.compile(r'\.json$')

#: Flask app instance, must be bound globally
app = flask.Flask(__name__, static_folder=str(_STATIC_FOLDER))


def init(run_dir):
    """Initialize globals and populate simulation dir"""
    global _SIMULATION_DIR
    global _WORK_DIR
    _WORK_DIR = run_dir.join('srw_tmp')
    _SIMULATION_DIR = run_dir.join('srw_simulations')
    if not _SIMULATION_DIR.check():
        pkio.mkdir_parent(_SIMULATION_DIR)
        for s in _examples():
            _save_new_simulation(s, is_response=False)


@app.route('/srw/copy-simulation', methods=('GET', 'POST'))
def srw_copy_simulation():
    """Takes the specified simulation and returns a newly named copy with the suffix (copy X)"""
    data = _open_json_file(_simulation_filename(_json_input('simulationId')))
    base_name = data['models']['simulation']['name']
    names = _iterate_simulation_datafiles(_simulation_name)
    count = 0
    while True:
        count += 1
        name = base_name + ' (copy{})'.format(' {}'.format(count) if count > 1 else '')
        if name in names and count < 100:
            continue
        break
    data['models']['simulation']['name'] = name
    return _save_new_simulation(data)


@app.route('/srw/delete-simulation', methods=('GET', 'POST'))
def srw_delete_simulation():
    pkio.unchecked_remove(_simulation_filename(_json_input('simulationId')))
    return '{}'


@app.route('/srw/new-simulation', methods=('GET', 'POST'))
def srw_new_simulation():
    data = _open_json_file(_STATIC_FOLDER.join('json/default.json'))
    data['models']['simulation']['name'] = _json_input('name')
    return _save_new_simulation(data)


@app.route('/srw/python-source/<simulation_id>')
def srw_python_source(simulation_id):
    data = _open_json_file(_simulation_filename(simulation_id))
    # ensure the whole source gets generated, not up to the last breakout report
    if 'report' in data:
        del data['report']
    return flask.Response(
        '{}{}'.format(_generate_parameters_file(data), sirepo.srw_template.run_all_text()),
        mimetype='text/plain',
    )


@app.route('/srw')
def srw_root():
    return app.send_static_file('html/srw.html')


@app.route('/srw/run', methods=('GET', 'POST'))
def srw_run():
    http_text = _read_http_input()
    data = json.loads(http_text)
    with pkio.save_chdir(_work_dir(), mkdir=True) as wd:
        pkdp('work_dir={}', wd)
        _save_simulation_json(data)
        pkio.write_text('in.json', http_text)
        pkio.write_text('srw_parameters.py', _generate_parameters_file(data))
        #TODO(pjm): need a kill timer for long calculates, ex. Intensity Report
        # with ebeam horizontal position of 0.05
        p = Popen(['sirepo', 'srw', 'run'], stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        if p.returncode != 0:
            pkdp('run_srw.py failed with status code: {}, dir: {}, error: {}'.format(p.returncode, wd, err))
            m = re.search('Error: ([^\n]+)', err)
            if m:
                error_text = m.group(1)
            else:
                error_text = 'an error occurred'
            return json.dumps({
                'error': error_text,
            })
        with open('out.json') as f:
            data = f.read()
    # Remove only in the case of a non-error/exception. If there's an error, we may
    # want to debug
    pkio.unchecked_remove(wd)
    return data


@app.route('/srw/simulation/<simulation_id>')
def srw_simulation_data(simulation_id):
    res = _iterate_simulation_datafiles(_find_simulation_data, {'simulationId': simulation_id})
    if len(res):
        if len(res) > 1:
            pkdp('multiple data files found for id: {}'.format(simulation_id))
        return json.dumps(res[0])
    flask.abort(404)


@app.route('/srw/simulation-list')
def srw_simulation_list():
    return json.dumps(
        sorted(
            _iterate_simulation_datafiles(_process_simulation_list),
            key=lambda row: row['last_modified'],
            reverse=True
        )
    )


def _escape_and_scale_value(k, v):
    v = str(v).replace("'", '')
    if k in _SCALE_VALUES:
        v = float(v) / 1000;
    return v


def _find_simulation_data(res, path, data, params):
    if str(data['models']['simulation']['simulationId']) == params['simulationId']:
        res.append(data)


def _flatten_data(d, res, prefix=''):
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            _flatten_data(v, res, prefix + k + '_')
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = _escape_and_scale_value(k, v)
    return res


def _generate_parameters_file(data):
    if 'report' in data and re.search('watchpointReport', data['report']):
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][data['report']]
    v = _flatten_data(data['models'], {})
    beamline = data['models']['beamline']
    last_id = None
    if 'report' in data:
        m = re.search('watchpointReport(\d+)', data['report'])
        if m:
            last_id = int(m.group(1))
    v['beamlineOptics'] = sirepo.srw_template.generate_beamline_optics(data['models'], last_id)
    v['beamlineFirstElementPosition'] = beamline[0]['position'] if len(beamline) else 20
    # initial drift = 1/2 undulator length + 2 periods
    v['electronBeamInitialDrift'] = -0.5 * float(data['models']['undulator']['length']) - 2 * float(data['models']['undulator']['period']) / 1000 + float(data['models']['undulator']['longitudinalPosition'])
    return sirepo.srw_template.TEMPLATE.format(**v).decode('unicode-escape')


def _examples():
    global _SRW_EXAMPLES
    if not _SRW_EXAMPLES:
        files = pkio.walk_tree(pkresource.filename('srw_examples'), _JSON_FILE_RE)
        _SRW_EXAMPLES = [_open_json_file(str(f)) for f in files]
    return _SRW_EXAMPLES


def _iterate_simulation_datafiles(op, params=None):
    res = []
    for path in pkio.walk_tree(_SIMULATION_DIR, _JSON_FILE_RE):
        try:
            op(res, path, _open_json_file(path), params)
        except ValueError:
            pkdp('unparseable json file: {}'.format(path))

    return res


def _json_input(field):
    return json.loads(_read_http_input())[field]


def _open_json_file(path):
    with open(str(path)) as f:
        return json.load(f)
    pkdp(path)

def _process_simulation_list(res, path, data, params):
    res.append({
        'simulationId': data['models']['simulation']['simulationId'],
        'name': data['models']['simulation']['name'],
        'last_modified': datetime.datetime.fromtimestamp(
            os.path.getmtime(str(path))
        ).strftime('%Y-%m-%d %H:%M'),
    })


def _read_http_input():
    return flask.request.data.decode('unicode-escape')


def _save_new_simulation(data, is_response=True):
    #TODO(pjm): use database sequence for Id
    i = _simulation_id()
    data['models']['simulation']['simulationId'] = i
    _save_simulation_json(data)
    if is_response:
        return srw_simulation_data(i)


def _save_simulation_json(data):
    si = data['models']['simulation']['simulationId']
    with open(_simulation_filename(si), 'w') as outfile:
        json.dump(data, outfile)


def _simulation_filename(value):
    if not _ID_RE.search(value):
        raise RuntimeError('{}: invalid simulation id'.format(value))
    return str(_SIMULATION_DIR.join(value)) + '.json'


def _simulation_id():
    """Generate cryptographically secure random string"""
    r = random.SystemRandom()
    return ''.join(r.choice(_ID_CHARS) for x in range(_ID_LEN))


def _simulation_name(res, path, data, params):
    res.append(data['models']['simulation']['name'])


def _work_dir():
    fmt = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S_{}')
    for i in range(3):
        d = _WORK_DIR.join(fmt.format(random.randint(1000, 9999)))
        if not d.check():
            return d
    raise RuntimeError('{}: failed to create unique directory name'.format(d))
