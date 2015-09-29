# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import datetime
import errno
import json
import os
import random
import re
import string
import subprocess
import threading

from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
import flask
import numconv
import py
import sirepo.template.srw
import sirepo.template.warp

#: Implemented apps
_APP_NAMES = ['srw', 'warp']

#: Known emporary directory where simulation dirs are created
_WORK_DIR = None

#: Where simulation config files are found
_SIMULATION_DIR = {}

#: Cache of schemas keyed by app name
_SCHEMA_CACHE = {}

#: Where server files and static files are found
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Verify ID
_ID_RE = re.compile('^[{}]{{{}}}$'.format(_ID_CHARS, _ID_LEN))

#: Is file name json
_JSON_FILE_RE = re.compile(r'\.json$')

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:Warning|Exception|Error): ([^\n]+)')

with open(str(_STATIC_FOLDER.join('json/schema-common.json'))) as f:
    _SCHEMA_COMMON = json.load(f)

#: Flask app instance, must be bound globally
app = flask.Flask(__name__, static_folder=str(_STATIC_FOLDER), template_folder=str(_STATIC_FOLDER))

def init(run_dir):
    """Initialize globals and populate simulation dir"""
    global _WORK_DIR
    run_dir = py.path.local(run_dir)
    _WORK_DIR = run_dir.join('tmp')
    if not _WORK_DIR.check():
        pkio.mkdir_parent(_WORK_DIR)
    for app in _APP_NAMES:
        _SIMULATION_DIR[app] = run_dir.join('{}_simulations'.format(app))
        if not _SIMULATION_DIR[app].check():
            pkio.mkdir_parent(_SIMULATION_DIR[app])
            for s in _examples(app):
                _save_new_simulation(app, s, is_response=False)


@app.route(_SCHEMA_COMMON['route']['copySimulation'], methods=('GET', 'POST'))
def app_copy_simulation():
    """Takes the specified simulation and returns a newly named copy with the suffix (copy X)"""
    simulation_type = _json_input('simulationType')
    data = _open_json_file(simulation_type, _simulation_filename(simulation_type, _json_input('simulationId')))
    base_name = data['models']['simulation']['name']
    names = _iterate_simulation_datafiles(simulation_type, _simulation_name)
    count = 0
    while True:
        count += 1
        name = base_name + ' (copy{})'.format(' {}'.format(count) if count > 1 else '')
        if name in names and count < 100:
            continue
        break
    data['models']['simulation']['name'] = name
    return _save_new_simulation(simulation_type, data)


@app.route('/favicon.ico')
def app_route_favicon():
    """Routes to favicon.ico file."""
    return flask.send_from_directory(
        str(_STATIC_FOLDER.join('img')),
        'favicon.ico', mimetype='image/vnd.microsoft.icon'
    )

@app.route(_SCHEMA_COMMON['route']['deleteSimulation'], methods=('GET', 'POST'))
def app_delete_simulation():
    pkio.unchecked_remove(_simulation_filename(_json_input('simulationType'), _json_input('simulationId')))
    return '{}'


@app.route(_SCHEMA_COMMON['route']['newSimulation'], methods=('GET', 'POST'))
def app_new_simulation():
    simulation_type = _json_input('simulationType')
    data = _open_json_file(simulation_type, _STATIC_FOLDER.join('json/{}-default.json'.format(simulation_type)))
    data['models']['simulation']['name'] = _json_input('name')
    return _save_new_simulation(simulation_type, data)


@app.route(_SCHEMA_COMMON['route']['pythonSource'])
def app_python_source(simulation_type, simulation_id):
    data = _open_json_file(simulation_type, _simulation_filename(simulation_type, simulation_id))
    template = _template_for_simulation_type(simulation_type)
    # ensure the whole source gets generated, not up to the last breakout report
    if 'report' in data:
        del data['report']
    return flask.Response(
        '{}{}'.format(
            template.generate_parameters_file(data, _schema_cache(simulation_type)),
            template.run_all_text()),
        mimetype='text/plain',
    )


@app.route(_SCHEMA_COMMON['route']['root'])
def app_root(simulation_type):
    return flask.render_template(
        'html/' + simulation_type + '.html',
        version=_SCHEMA_COMMON['version'],
    )


@app.route(_SCHEMA_COMMON['route']['runSimulation'], methods=('GET', 'POST'))
def app_run():
    data = json.loads(_read_http_input())
    simulation_type = data['simulationType']
    data = _fixup_old_data(simulation_type, data)
    template = _template_for_simulation_type(simulation_type)
    wd = _work_dir()
    _save_simulation_json(simulation_type, data)
    with open(str(wd.join('in.json')), 'w') as outfile:
        json.dump(data, outfile)
    pkio.write_text(
        wd.join(simulation_type + '_parameters.py'),
        template.generate_parameters_file(data, _schema_cache(simulation_type)),
    )
    template.prepare_aux_files(wd)
    err = _Command(['sirepo', simulation_type, 'run', str(wd)], template.MAX_SECONDS).run_and_read()
    if err:
        i = _id(data)
        pkdp('error: simulationId={}, dir={}, out={}', i, wd, err)
        return flask.jsonify({
            'error': _error_text(err),
            'simulationId': i,
        })
    data = pkio.read_text(wd.join('out.json'))
    # Remove only in the case of a non-error/exception. If there's an error, we may
    # want to debug
    pkio.unchecked_remove(wd)
    return data


@app.route(_SCHEMA_COMMON['route']['simulationData'])
def app_simulation_data(simulation_type, simulation_id):
    res = _iterate_simulation_datafiles(
        simulation_type,
        _find_simulation_data,
        {'simulationId': simulation_id},
    )
    if len(res):
        if len(res) > 1:
            pkdp('multiple data files found for id: {}'.format(simulation_id))
        return flask.jsonify(res[0])
    flask.abort(404)


@app.route(_SCHEMA_COMMON['route']["listSimulations"], methods=('GET', 'POST'))
def app_simulation_list(simulation_type):
    simulation_type = _json_input('simulationType')
    return json.dumps(
        sorted(
            _iterate_simulation_datafiles(simulation_type, _process_simulation_list),
            key=lambda row: row['last_modified'],
            reverse=True
        )
    )


@app.route(_SCHEMA_COMMON['route']['simulationSchema'], methods=('GET', 'POST'))
def app_simulation_schema():
    sim_type = flask.request.form['simulationType']
    return flask.jsonify(_schema_cache(sim_type))


def _error_text(err):
    """Parses error from subprocess"""
    m = re.search(_SUBPROCESS_ERROR_RE, err)
    if m:
        return m.group(1)
    return 'a system error occurred'


def _find_simulation_data(res, path, data, params):
    if str(_id(data)) == params['simulationId']:
        res.append(data)


def _fixup_old_data(simulation_type, data):
    if 'version' in data and data['version'] == _SCHEMA_COMMON['version']:
        return data
    if simulation_type == 'srw':
        sirepo.template.srw.fixup_old_data(data)
    data['version'] = _SCHEMA_COMMON['version']
    return data


def _examples(app):
    files = pkio.walk_tree(pkresource.filename('{}_examples'.format(app)), _JSON_FILE_RE)
    return [_open_json_file(app, str(f)) for f in files]


def _id(data):
    """Extract id from data"""
    return str(data['models']['simulation']['simulationId'])


def _iterate_simulation_datafiles(simulation_type, op, params=None):
    res = []
    for path in pkio.walk_tree(_SIMULATION_DIR[simulation_type], _JSON_FILE_RE):
        try:
            op(res, path, _open_json_file(simulation_type, path), params)
        except ValueError:
            pkdp('unparseable json file: {}', path)

    return res


def _json_input(field):
    return json.loads(_read_http_input())[field]


def _open_json_file(simulation_type, path):
    with open(str(path)) as f:
        return _fixup_old_data(simulation_type, json.load(f))


def _process_simulation_list(res, path, data, params):
    res.append({
        'simulationId': _id(data),
        'name': data['models']['simulation']['name'],
        'last_modified': datetime.datetime.fromtimestamp(
            os.path.getmtime(str(path))
        ).strftime('%Y-%m-%d %H:%M'),
    })


def _read_http_input():
    return flask.request.data.decode('unicode-escape')


def _save_new_simulation(simulation_type, data, is_response=True):
    #TODO(pjm): use database sequence for Id
    r = random.SystemRandom()
    # Generate cryptographically secure random string
    i = ''.join(r.choice(_ID_CHARS) for x in range(_ID_LEN))
    data['models']['simulation']['simulationId'] = i
    _save_simulation_json(simulation_type, data)
    if is_response:
        return app_simulation_data(simulation_type, i)


def _save_simulation_json(simulation_type, data):
    si = _id(data)
    with open(_simulation_filename(simulation_type, si), 'w') as outfile:
        json.dump(data, outfile)


def _schema_cache(sim_type):
    if sim_type in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[sim_type]
    with open(str(_STATIC_FOLDER.join('json/{}-schema.json'.format(sim_type)))) as f:
        schema = json.load(f)
    schema.update(_SCHEMA_COMMON)
    schema['simulationType'] = sim_type
    _SCHEMA_CACHE[sim_type] = schema
    return schema


def _simulation_filename(simulation_type, value):
    if not _ID_RE.search(value):
        raise RuntimeError('{}: invalid simulation id'.format(value))
    return str(_SIMULATION_DIR[simulation_type].join(value)) + '.json'


def _simulation_name(res, path, data, params):
    res.append(data['models']['simulation']['name'])


def _template_for_simulation_type(simulation_type):
    if simulation_type == 'srw':
        return sirepo.template.srw
    if simulation_type == 'warp':
        return sirepo.template.warp
    raise RuntimeError('{}: invalid simulation_type'.format(simulation_type))


def _work_dir():
    fmt = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S_{}')
    for i in range(5):
        d = _WORK_DIR.join(fmt.format(random.randint(1000, 9999)))
        try:
            os.mkdir(str(d))
            return d
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            raise
    raise RuntimeError('{}: failed to create unique directory name'.format(d))


class _Command(threading.Thread):
    """Run a command in a thread, and kill after timeout"""

    def __init__(self, cmd, timeout):
        super(_Command, self).__init__()
        # Daemon threads are stopped abruptly so won't hang the server
        self.daemon = True
        self.cmd = cmd
        self.timeout = timeout
        self.process = None
        self.out = ''

    def run(self):
        self.process = subprocess.Popen(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.out = self.process.communicate()[0]

    def run_and_read(self):
        self.start()
        self.join(self.timeout)
        try:
            self.process.kill()
            pkdp('Timeout: cmd={}', self.cmd)
            # Thread should exit, but make sure
            self.join(2)
            return self.out + '\nError: simulation took too long'
        except OSError as e:
            if e.errno != errno.ESRCH:
                raise
        if self.process.returncode != 0:
            pkdp('Error: cmd={}, returncode={}', self.cmd, self.process.returncode)
            return self.out + '\nError: simulation failed'
        return None
