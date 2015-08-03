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
import shutil
import string
import subprocess
import threading

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

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Verify ID
_ID_RE = re.compile('^[{}]{{{}}}$'.format(_ID_CHARS, _ID_LEN))

#: Is file name json
_JSON_FILE_RE = re.compile(r'\.json$')

#: Parsing errors from SRW
_SRW_ERROR_RE = re.compile(r'\bError: ([^\n]+)')

#: How long before killing SRW process
_SRW_MAX_SECONDS = 30

with open(str(_STATIC_FOLDER.join('json/schema.json'))) as f:
    _APP_SCHEMA = json.load(f)

#: Flask app instance, must be bound globally
app = flask.Flask(__name__, static_folder=str(_STATIC_FOLDER), template_folder=str(_STATIC_FOLDER))

def init(run_dir):
    """Initialize globals and populate simulation dir"""
    global _SIMULATION_DIR
    global _WORK_DIR
    run_dir = py.path.local(run_dir)
    _WORK_DIR = run_dir.join('srw_tmp')
    _SIMULATION_DIR = run_dir.join('srw_simulations')
    if not _SIMULATION_DIR.check():
        pkio.mkdir_parent(_SIMULATION_DIR)
        for s in _examples():
            _save_new_simulation(s, is_response=False)


@app.route(_APP_SCHEMA['route']['copySimulation'], methods=('GET', 'POST'))
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


@app.route(_APP_SCHEMA['route']['deleteSimulation'], methods=('GET', 'POST'))
def srw_delete_simulation():
    pkio.unchecked_remove(_simulation_filename(_json_input('simulationId')))
    return '{}'


@app.route(_APP_SCHEMA['route']['newSimulation'], methods=('GET', 'POST'))
def srw_new_simulation():
    data = _open_json_file(_STATIC_FOLDER.join('json/default.json'))
    data['models']['simulation'] = {
        'name': _json_input('name'),
    }
    return _save_new_simulation(data)


@app.route(_APP_SCHEMA['route']['pythonSource'])
def srw_python_source(simulation_id):
    data = _open_json_file(_simulation_filename(simulation_id))
    # ensure the whole source gets generated, not up to the last breakout report
    if 'report' in data:
        del data['report']
    return flask.Response(
        '{}{}'.format(sirepo.srw_template.generate_parameters_file(data, _APP_SCHEMA), sirepo.srw_template.run_all_text()),
        mimetype='text/plain',
    )


@app.route(_APP_SCHEMA['route']['root'])
def srw_root():
    return flask.render_template(
        'html/srw.html',
        version=_APP_SCHEMA['version'],
    )


@app.route(_APP_SCHEMA['route']['runSimulation'], methods=('GET', 'POST'))
def srw_run():
    http_text = _read_http_input()
    data = _fixup_old_data(json.loads(http_text))
    with pkio.save_chdir(_work_dir(), mkdir=True) as wd:
        pkdp('dir={}', wd)
        _save_simulation_json(data)
        pkio.write_text('in.json', http_text)
        pkio.write_text('srw_parameters.py', sirepo.srw_template.generate_parameters_file(data, _APP_SCHEMA))
        shutil.copyfile(pkresource.filename('static/dat/mirror_1d.dat'), 'mirror_1d.dat')
        #TODO(pjm): need a kill timer for long calculates, ex. Intensity Report
        # with ebeam horizontal position of 0.05
        err = _Command(['sirepo', 'srw', 'run'], _SRW_MAX_SECONDS).run_and_read()
        if err:
            i = _id(data)
            pkdp('error: simulationId={}, dir={}, out={}', i, wd, err)
            return json.dumps({
                'error': _error_text(err),
                'simulationId': i,
            })
        with open('out.json') as f:
            data = f.read()
    # Remove only in the case of a non-error/exception. If there's an error, we may
    # want to debug
    pkio.unchecked_remove(wd)
    return data


@app.route(_APP_SCHEMA['route']['simulationData'])
def srw_simulation_data(simulation_id):
    res = _iterate_simulation_datafiles(
        _find_simulation_data,
        {'simulationId': simulation_id},
    )
    if len(res):
        if len(res) > 1:
            pkdp('multiple data files found for id: {}'.format(simulation_id))
        return json.dumps(res[0])
    flask.abort(404)


@app.route(_APP_SCHEMA['route']["listSimulations"])
def srw_simulation_list():
    return json.dumps(
        sorted(
            _iterate_simulation_datafiles(_process_simulation_list),
            key=lambda row: row['last_modified'],
            reverse=True
        )
    )


def _error_text(err):
    """Parses error from SRW"""
    m = re.search(_SRW_ERROR_RE, err)
    if m:
        return m.group(1)
    return 'a system error occurred'


def _find_simulation_data(res, path, data, params):
    if str(_id(data)) == params['simulationId']:
        res.append(data)


def _fixup_old_data(data):
    if 'version' in data and data['version'] == _APP_SCHEMA['version']:
        return data
    if 'post_propagation' in data['models']:
        data['models']['postPropagation'] = data['models']['post_propagation']
        del data['models']['post_propagation']
    if 'watchpointReport' in data['models']:
        del data['models']['watchpointReport']
    for item in data['models']['beamline']:
        if item['type'] == 'aperture' or item['type'] == 'obstacle':
            if not item.get('shape'):
                item['shape'] = 'r'
            if not item.get('horizontalOffset'):
                item['horizontalOffset'] = 0
            if not item.get('verticalOffset'):
                item['verticalOffset'] = 0
        elif item['type'] == 'mirror':
            if not item.get('heightProfileFile'):
                item['heightProfileFile'] = 'mirror_1d.dat'
    data['version'] = _APP_SCHEMA['version']
    return data


def _examples():
    global _SRW_EXAMPLES
    if not _SRW_EXAMPLES:
        files = pkio.walk_tree(pkresource.filename('srw_examples'), _JSON_FILE_RE)
        _SRW_EXAMPLES = [_open_json_file(str(f)) for f in files]
    return _SRW_EXAMPLES


def _id(data):
    """Extract id from data"""
    return str(data['models']['simulation']['simulationId'])

def _iterate_simulation_datafiles(op, params=None):
    res = []
    for path in pkio.walk_tree(_SIMULATION_DIR, _JSON_FILE_RE):
        try:
            op(res, path, _open_json_file(path), params)
        except ValueError:
            pkdp('unparseable json file: {}', path)

    return res


def _json_input(field):
    return json.loads(_read_http_input())[field]


def _open_json_file(path):
    with open(str(path)) as f:
        return _fixup_old_data(json.load(f))


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


def _save_new_simulation(data, is_response=True):
    #TODO(pjm): use database sequence for Id
    i = _simulation_id()
    data['models']['simulation']['simulationId'] = i
    _save_simulation_json(data)
    if is_response:
        return srw_simulation_data(i)


def _save_simulation_json(data):
    si = _id(data)
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
