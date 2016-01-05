# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import datetime
import errno
import glob
import json
import os
import os.path
import random
import re
import signal
import string
import sys
import subprocess
import threading
import time
import werkzeug
import werkzeug.exceptions

from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
from pykern import pkcollections
import beaker.middleware
import flask
import flask.sessions
import numconv
import py
import sirepo.template.srw
import sirepo.template.warp

#: Implemented apps
_APP_NAMES = ['srw', 'warp']

#: Cache of schemas keyed by app name
_SCHEMA_CACHE = {}

#: Where server files and static files are found
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

#: How to find examples in resources
_EXAMPLE_DIR_FORMAT = '{}_examples'

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Verify ID
_ID_RE = re.compile('^[{}]{{{}}}$'.format(_ID_CHARS, _ID_LEN))

#: Json files
_JSON_SUFFIX = '.json'

#: Simulation file name is globally unique to avoid collisions with simulation output
_SIMULATION_DATA_FILE = 'sirepo-data' + _JSON_SUFFIX

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:Warning|Exception|Error): ([^\n]+)')

#: Subdir shere to run the simulation
_SIMULATION_RUN_DIR = 'run'

#: Attribute in session object
_UID_ATTR = 'uid'

#: where users live under db_dir
_LIB_DIR = 'lib'

#: where users live under db_dir
_USER_ROOT_DIR = 'user'

#: where users live under db_dir
_BEAKER_DATA_DIR = 'beaker'

#: where users live under db_dir
_BEAKER_LOCK_DIR = 'lock'

#: What to exec (root_pkg)
_ROOT_CMD = 'sirepo'


with open(str(_STATIC_FOLDER.join('json/schema-common.json'))) as f:
    _SCHEMA_COMMON = json.load(f)


#: Flask app instance, must be bound globally
app = None


class BeakerSession(flask.sessions.SessionInterface):
    """Session manager for Flask using Beaker.

    Stores session info in files in sirepo.server.data_dir. Minimal info kept
    in session.
    """
    def __init__(self, app=None):
        if app is None:
            self.app = None
        else:
            self.init_app(app)

    def sirepo_init_app(self, app, db_dir):
        """Initialize _cfg with db_dir and register self with Flask

        Args:
            app (flask): Flask application object
            db_dir (py.path.local): db_dir passed on command line
        """
        app.sirepo_db_dir = db_dir
        data_dir = db_dir.join(_BEAKER_DATA_DIR)
        lock_dir = data_dir.join(_BEAKER_LOCK_DIR)
        pkio.mkdir_parent(lock_dir)
        sc = {
            'session.auto': True,
            'session.cookie_expires': False,
            'session.type': 'file',
            'session.data_dir': str(data_dir),
            'session.lock_dir': str(lock_dir),
        }
        #TODO(robnagler) Generalize? seems like we'll be shadowing lots of config
        for k in _cfg.session:
            sc['session.' + k] = _cfg.session[k]
        app.wsgi_app = beaker.middleware.SessionMiddleware(app.wsgi_app, sc)
        app.session_interface = self

    def open_session(self, app, request):
        """Called by flask to create the session"""
        return request.environ['beaker.session']

    def save_session(self, *args, **kwargs):
        """Necessary to complete abstraction, but Beaker autosaves"""
        pass


app = flask.Flask(
    __name__,
    static_folder=str(_STATIC_FOLDER),
    template_folder=str(_STATIC_FOLDER),
)


def init(db_dir):
    """Initialize globals and populate simulation dir"""
    BeakerSession().sirepo_init_app(app, py.path.local(db_dir))


@app.route(_SCHEMA_COMMON['route']['clearFrames'], methods=('GET', 'POST'))
def app_clear_frames():
    """Clear animation frames for the simulation."""
    data = _json_input()
    _simulation_run_dir(data, remove_dir=True)
    return '{}'


@app.route(_SCHEMA_COMMON['route']['copySimulation'], methods=('GET', 'POST'))
def app_copy_simulation():
    """Takes the specified simulation and returns a newly named copy with the suffix (copy X)"""
    req = _json_input()
    simulation_type = req['simulationType']
    data = _open_json_file(simulation_type, sid=req['simulationId'])
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
    data['models']['simulation']['isExample'] = ''
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
    data = _json_input()
    pkio.unchecked_remove(_simulation_dir(data['simulationType'], data['simulationId']))
    return '{}'


@app.route(_SCHEMA_COMMON['route']['downloadDataFile'], methods=('GET', 'POST'))
def app_download_data_file(simulation_type, simulation_id, model_or_frame):
    data = {
        'simulationType': simulation_type,
        'simulationId': simulation_id,
    }
    frame_index = -1
    if re.match(r'^\d+$', model_or_frame):
        frame_index = int(model_or_frame)
    else:
        data['report'] = model_or_frame
    run_dir = _simulation_run_dir(data)
    template = _template_for_simulation_type(simulation_type)
    filename, content, content_type = template.get_data_file(run_dir, frame_index)
    response = flask.make_response(content)
    response.mimetype = content_type
    response.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return response


@app.route(_SCHEMA_COMMON['route']['downloadFile'], methods=('GET', 'POST'))
def app_download_file(simulation_type, simulation_id, filename):
    lib = _simulation_lib_dir(simulation_type)
    p = lib.join(werkzeug.secure_filename(filename))
    return flask.send_file(str(p))

@app.route(_SCHEMA_COMMON['route']['findByName'], methods=('GET', 'POST'))
def app_find_by_name(simulation_type, application_mode, simulation_name):
    rows = _iterate_simulation_datafiles(simulation_type, _process_simulation_list, {
        'simulation.name': simulation_name,
    })
    if len(rows) == 0:
        for s in _examples(simulation_type):
            if s['models']['simulation']['name'] == simulation_name:
                _save_new_simulation(simulation_type, s, is_response=False)
                rows = _iterate_simulation_datafiles(simulation_type, _process_simulation_list, {
                    'simulation.name': simulation_name,
                })
                break

    for row in rows:
        if application_mode == 'light-sources':
            redirect_uri = '/{}#/simulations?simulation.facility={}&application_mode={}'.format(
                simulation_type, flask.escape(row['simulation']['facility']), application_mode)
        else:
            redirect_uri = '/{}#/source/{}?application_mode={}'.format(
                simulation_type, row['simulationId'], application_mode)
        # redirect using javascript for safari browser which doesn't support hash redirects
        return flask.render_template(
            'html/javascript-redirect.html',
            redirect_uri=redirect_uri
        )
    werkzeug.exceptions.abort(404)


@app.route(_SCHEMA_COMMON['route']['newSimulation'], methods=('GET', 'POST'))
def app_new_simulation():
    new_simulation_data = _json_input()
    simulation_type = new_simulation_data['simulationType']
    data = _open_json_file(
        simulation_type,
        _STATIC_FOLDER.join('json', '{}-default.json'.format(simulation_type)),
    )
    data['models']['simulation']['name'] = new_simulation_data['name']
    _template_for_simulation_type(simulation_type).new_simulation(data, new_simulation_data)
    return _save_new_simulation(simulation_type, data)


@app.route(_SCHEMA_COMMON['route']['pythonSource'])
def app_python_source(simulation_type, simulation_id):
    data = _open_json_file(simulation_type, sid=simulation_id)
    template = _template_for_simulation_type(simulation_type)
    # ensure the whole source gets generated, not up to the last breakout report
    if 'report' in data:
        del data['report']
    return flask.Response(
        '{}{}'.format(
            template.generate_parameters_file(data, _schema_cache(simulation_type), None),
            template.run_all_text()),
        mimetype='text/plain',
    )


@app.route(_SCHEMA_COMMON['route']['root'])
def app_root(simulation_type):
    return flask.render_template(
        'html/index.html',
        version=_SCHEMA_COMMON['version'],
        app_name=simulation_type,
    )


@app.route(_SCHEMA_COMMON['route']['runSimulation'], methods=('GET', 'POST'))
def app_run():
    data = _json_input()
    sid = _sid(data)
    err = _start_simulation(data).run_and_read()
    run_dir = _simulation_run_dir(data)
    if err:
        pkdp('error: sid={}, dir={}, out={}', sid, run_dir, err)
        return flask.jsonify({
            'error': _error_text(err),
            'simulationId': sid,
        })
    return pkio.read_text(run_dir.join('out.json'))


@app.route(_SCHEMA_COMMON['route']['runBackground'], methods=('GET', 'POST'))
def app_run_background():
    data = _json_input()
    sid = _sid(data)
    #TODO(robnagler) race condition. Need to lock the simulation
    if _cfg.daemonizer.is_running(sid):
        #TODO(robnagler) return error to user if in different window
        pkdp('ignoring second call to runBackground: {}'.format(sid))
        return '{}'
    status = data['models']['simulationStatus']
    status['state'] = 'running'
    #TODO: Javascript weirdness. Should normalize time as UTC
    status['startTime'] = int(time.time() * 1000)
    _start_simulation(data, run_async=True)
    return flask.jsonify({
        'state': status['state'],
        'startTime': status['startTime'],
    })


@app.route(_SCHEMA_COMMON['route']['runCancel'], methods=('GET', 'POST'))
def app_run_cancel():
    data = _json_input()
    data['models']['simulationStatus']['state'] = 'canceled'
    simulation_type = data['simulationType']
    _save_simulation_json(simulation_type, data)
    _cfg.daemonizer.kill(_sid(data))
    # the last frame file may not be finished, remove it
    t = _template_for_simulation_type(simulation_type)
    t.remove_last_frame(_simulation_run_dir(data))
    return '{}'


@app.route(_SCHEMA_COMMON['route']['runStatus'], methods=('GET', 'POST'))
def app_run_status():
    data = _json_input()
    sid = _sid(data)
    simulation_type = data['simulationType']
    template = _template_for_simulation_type(simulation_type)
    run_dir = _simulation_run_dir(data)
    if _cfg.daemonizer.is_running(sid):
        completion = template.background_percent_complete(data, run_dir, True)
        state = 'running'
    else:
        data = _open_json_file(simulation_type, sid=sid)
        state = data['models']['simulationStatus']['state']
        completion = template.background_percent_complete(data, run_dir, False)
        if state == 'running':
            if completion['frame_count'] == completion['total_frames']:
                state = 'completed'
            else:
                state = 'canceled'
            data['models']['simulationStatus']['state'] = state
            _save_simulation_json(data['simulationType'], data)
    return flask.jsonify({
        'state': state,
        'percentComplete': completion['percent_complete'],
        'frameCount': completion['frame_count'],
        'totalFrames': completion['total_frames'],
    })


@app.route(_SCHEMA_COMMON['route']['simulationData'])
def app_simulation_data(simulation_type, simulation_id):
    response = flask.jsonify(_open_json_file(simulation_type, sid=simulation_id))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


@app.route(_SCHEMA_COMMON['route']['simulationFrame'])
def app_simulation_frame(frame_id):
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    data = dict(zip(keys, frame_id.split('-')))
    run_dir = _simulation_run_dir(data)
    response = flask.jsonify(_template_for_simulation_type(
        data['simulationType']).get_simulation_frame(run_dir, data))
    now = datetime.datetime.utcnow()
    expires = now + datetime.timedelta(365)
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
    response.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return response


@app.route(_SCHEMA_COMMON['route']['listFiles'], methods=('GET', 'POST'))
def app_file_list(simulation_type, simulation_id):
    res = []
    d = _simulation_lib_dir(simulation_type)
    for f in glob.glob(str(d.join('*.*'))):
        if os.path.isfile(f):
            res.append(os.path.basename(f))
    res.sort()
    return json.dumps(res)


@app.route(_SCHEMA_COMMON['route']['listSimulations'], methods=('GET', 'POST'))
def app_simulation_list():
    input = _json_input()
    simulation_type = input['simulationType']
    search = input['search'] if 'search' in input else None
    return json.dumps(
        sorted(
            _iterate_simulation_datafiles(simulation_type, _process_simulation_list, search),
            key=lambda row: row['last_modified'],
            reverse=True
        )
    )


@app.route(_SCHEMA_COMMON['route']['simulationSchema'], methods=('GET', 'POST'))
def app_simulation_schema():
    sim_type = flask.request.form['simulationType']
    return flask.jsonify(_schema_cache(sim_type))


@app.route('/light')
def light_landing_page():
    return flask.render_template(
        'html/sr-landing-page.html',
        version=_SCHEMA_COMMON['version'],
    )


@app.route('/sr')
def sr_landing_page():
    return flask.redirect('/light')


def _cfg_daemonizer(value):
    """Converts string to class"""
    if isinstance(value, (_Celery, _Background)):
        # Already initialized but may call initializer with original object
        return value
    if value == 'Celery':
        from sirepo import celery_tasks
        try:
            if not celery_tasks.celery.control.ping():
                print('You need to start Celery:\ncelery worker -A sirepo.celery_tasks -l info -c 1')
                sys.exit(1)
        except Exception:
            print('You need to start Rabbit:\ndocker run --rm --hostname rabbit --name rabbit -p 5672:5672 -p 15672:15672 rabbitmq')
            sys.exit(1)
        return _Celery

    elif value == 'Background':
        signal.signal(signal.SIGCHLD, _Background.sigchld_handler)
        return _Background
    else:
        raise AssertionError('{}: unknown daemonizer'.format(value))


def _cfg_session_secret(value):
    """Converts file to binary"""
    if not value:
        return 'dev dummy secret'
    with open(value) as f:
        return f.read()


@app.route(_SCHEMA_COMMON['route']['uploadFile'], methods=('GET', 'POST'))
def app_upload_file(simulation_type, simulation_id):
    f = flask.request.files['file']
    lib = _simulation_lib_dir(simulation_type)
    filename = werkzeug.secure_filename(f.filename)
    p = lib.join(filename)
    err = None
    if p.check():
        err = 'file exists: {}'.format(filename)
    if not err:
        f.save(str(p))
        err = _validate_data_file(p)
        if err:
            pkio.unchecked_remove(p)
    if err:
        return flask.jsonify({
            'error': err,
            'filename': filename,
            'simulationId': simulation_id,
        })
    return flask.jsonify({
        'filename': filename,
        'simulationId': simulation_id,
    })


def _error_text(err):
    """Parses error from subprocess"""
    m = re.search(_SUBPROCESS_ERROR_RE, err)
    if m:
        return m.group(1)
    return 'a system error occurred'


def _examples(app):
    files = pkio.walk_tree(
        pkresource.filename(_EXAMPLE_DIR_FORMAT.format(app)),
        re.escape(_JSON_SUFFIX) + '$',
    )
    return [_open_json_file(app, str(f)) for f in files]


def _fixup_old_data(simulation_type, data):
    if 'version' in data and data['version'] == _SCHEMA_COMMON['version']:
        return data
    _template_for_simulation_type(simulation_type).fixup_old_data(data)
    data['version'] = _SCHEMA_COMMON['version']
    return data


def _iterate_simulation_datafiles(simulation_type, op, search=None):
    res = []
    for path in glob.glob(
        str(_simulation_dir(simulation_type).join('*', _SIMULATION_DATA_FILE)),
    ):
        path = py.path.local(path)
        try:
            data = _open_json_file(simulation_type, path)
            if search and not _search_data(data, search):
                continue
            op(res, path, data)
        except ValueError:
            pkdp('unparseable json file: {}', path)
    return res


def _json_input():
    return json.loads(_read_http_input())


def _open_json_file(simulation_type, path=None, sid=None):
    if not path:
        path = _simulation_data_file(simulation_type, sid)
    if not os.path.isfile(str(path)):
        werkzeug.exceptions.abort(404)
    with open(str(path)) as f:
        return _fixup_old_data(simulation_type, json.load(f))


def _process_simulation_list(res, path, data):
    res.append({
        'simulationId': _sid(data),
        'name': data['models']['simulation']['name'],
        'last_modified': datetime.datetime.fromtimestamp(
            os.path.getmtime(str(path))
        ).strftime('%Y-%m-%d %H:%M'),
        'simulation': data['models']['simulation'],
    })


def _random_id(parent_dir):
    """Create a random id in parent_dir

    Args:
        parent_dir (py.path): where id should be unique
    Returns:
        str: id (not directory)
    """
    #TODO(pjm): use database sequence for Id
    pkio.mkdir_parent(parent_dir)
    r = random.SystemRandom()
    # Generate cryptographically secure random string
    for _ in range(5):
        i = ''.join(r.choice(_ID_CHARS) for x in range(_ID_LEN))
        d = parent_dir.join(i)
        try:
            os.mkdir(str(d))
            return i
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            raise
    raise RuntimeError('{}: failed to create unique direcotry'.format(parent_dir))


def _read_http_input():
    return flask.request.data.decode('unicode-escape')


def _report_name(data):
    """Extract report name from data

    Animations don't have a report name so we just return animation.

    Args:
        data (dict): passed in params
    Returns:
        str: name of the report requested in the data
    """
    try:
        return data['report']
    except KeyError:
        return 'animation'


def _save_new_simulation(simulation_type, data, is_response=True):
    sid = _random_id(_simulation_dir(simulation_type))
    data['models']['simulation']['simulationId'] = sid
    _save_simulation_json(simulation_type, data)
    if is_response:
        return app_simulation_data(simulation_type, sid)


def _save_simulation_json(simulation_type, data):
    sid = _sid(data)
    with open(_simulation_data_file(simulation_type, sid), 'w') as outfile:
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


def _search_data(data, search):
    for field in search:
        path = field.split('.')
        if len(path) == 1:
            continue
        path.insert(0, 'models')
        v = data
        for key in path:
            if key in v:
                v = v[key]
        if v != search[field]:
            return False
    return True


def _sid(data):
    """Extract id from data file

    Args:
        data (dict): data file parsed

    Returns:
        str: simulationId from data fiel
    """
    try:
        return str(data['simulationId'])
    except KeyError:
        return str(data['models']['simulation']['simulationId'])


def _simulation_data_file(simulation_type, sid):
    return str(_simulation_dir(simulation_type, sid).join(_SIMULATION_DATA_FILE))


def _simulation_dir(simulation_type, sid=None):
    """Generates simulation directory from sid and simulation_type

    Args:
        simulation_type (str): srw or warp
        sid (str): simulation id (optional)
    """
    d = _user_dir().join(simulation_type)
    if not sid:
        return d
    if not _ID_RE.search(sid):
        raise RuntimeError('{}: invalid simulation id'.format(sid))
    return d.join(sid)


def _simulation_lib_dir(simulation_type):
    """String name for user library dir

    Args:
        simulation_type: which app is this for

    Return:
        py.path: directory name
    """
    return _simulation_dir(simulation_type).join(_LIB_DIR)


def _simulation_name(res, path, data):
    """Extract name of simulation from data file

    Args:
        res (list): results of iteration
        path (py.path): full path to file
        data (dict): parsed json

    Returns:
        str: Human readable name for simulation
    """
    res.append(data['models']['simulation']['name'])


def _simulation_run_dir(data, remove_dir=False):
    """Where to run the simulation

    Args:
        data (dict): contains simulationType and simulationId
        remove_dir (bool): remove the directory [False]

    Returns:
        py.path: directory to run
    """
    d = _simulation_dir(data['simulationType'], _sid(data)).join(_report_name(data))
    if remove_dir:
        pkio.unchecked_remove(d)
    return d


def _start_simulation(data, run_async=False):
    """Setup and start the simulation.

    Args:
        data (dict): app data
        run_async (bool): run-background or run

    Returns:
        object: _Command or daemon instance
    """
    run_dir = _simulation_run_dir(data, remove_dir=True)
    pkio.mkdir_parent(run_dir)
    #TODO(robnagler) create a lock_dir -- what node/pid/thread to use?
    #   probably can only do with celery.
    simulation_type = data['simulationType']
    sid = _sid(data)
    data = _fixup_old_data(simulation_type, data)
    template = _template_for_simulation_type(simulation_type)
    _save_simulation_json(simulation_type, data)
    for d in _simulation_dir(simulation_type, sid), _simulation_lib_dir(simulation_type):
        for f in glob.glob(str(d.join('*.*'))):
            if os.path.isfile(f):
                py.path.local(f).copy(run_dir)
    with open(str(run_dir.join('in.json')), 'w') as outfile:
        json.dump(data, outfile)
    pkio.write_text(
        run_dir.join(simulation_type + '_parameters.py'),
        template.generate_parameters_file(
            data,
            _schema_cache(simulation_type),
            run_dir=run_dir,
        )
    )
    cmd = [_ROOT_CMD, simulation_type] \
        + ['run-background' if run_async else 'run'] + [str(run_dir)]
    if run_async:
        return _cfg.daemonizer(sid, run_dir, cmd)
    return _Command(cmd, template.MAX_SECONDS)


def _template_for_simulation_type(simulation_type):
    if simulation_type == 'srw':
        return sirepo.template.srw
    if simulation_type == 'warp':
        return sirepo.template.warp
    raise RuntimeError('{}: invalid simulation_type'.format(simulation_type))


def _user_dir():
    """User for the session

    Returns:
        str: unique id for user from flask session
    """
    if not _UID_ATTR in flask.session:
        _user_dir_create()
    d = _user_dir_name(flask.session[_UID_ATTR])
    if d.check():
        return d
    # Beaker session might have been deleted (in dev) so "logout" and "login"
    _user_dir_create()
    return _user_dir_name(flask.session[_UID_ATTR])


def _user_dir_create():
    """Create a user and initialize the directory"""
    uid = _random_id(_user_dir_name())
    # Must set before calling _simulation_dir
    flask.session[_UID_ATTR] = uid
    for app_name in _APP_NAMES:
        d = _simulation_dir(app_name)
        pkio.mkdir_parent(d)
        for s in _examples(app_name):
            _save_new_simulation(app_name, s, is_response=False)
        d = _simulation_lib_dir(app_name)
        pkio.mkdir_parent(d)
        for f in _template_for_simulation_type(app_name).static_lib_files():
            f.copy(d)


def _user_dir_name(uid=None):
    """String name for user name

    Args:
        uid (str): properly formated user name (optional)
    Return:
        py.path: directory name
    """
    d = app.sirepo_db_dir.join(_USER_ROOT_DIR)
    if not uid:
        return d
    return d.join(uid)


def _validate_data_file(path):
    """Ensure the data file contains parseable rows data"""
    try:
        count = 0
        with open(str(path)) as f:
            for line in f.readlines():
                parts = line.split("\t")
                if len(parts) > 0:
                    float(parts[0])
                if len(parts) > 1:
                    float(parts[1])
                    count += 1
        if count == 0:
            return 'no data rows found in file'
    except ValueError as e:
        return 'invalid file format: {}'.format(e)
    return None


class _Background(object):

    # Map of sid to instance
    _process = {}

    # mutex for _process
    _lock = threading.Lock()

    def __init__(self, sid, run_dir, cmd):
        with self._lock:
            assert not sid in self._process, \
                'Simulation already running: sid={}'.format(sid)
            self.in_kill = False
            self.sid = sid
            self.cmd = cmd
            self.run_dir = run_dir
            self._process[sid] = self
            self.pid = None
            # This command may blow up
            self.pid = self._create_daemon()

    @classmethod
    def is_running(cls, sid):
        with cls._lock:
            try:
                self = cls._process[sid]
            except KeyError:
                return False
            if self.in_kill:
                # Strange but true. The process is alive at this point so we
                # don't want to do anything like start a new process
                return True
            try:
                os.kill(self.pid, 0)
            except OSError:
                # Has to exist so no need to protect
                del self._process[sid]
                return False
        return True

    @classmethod
    def kill(cls, sid):
        self = None
        with cls._lock:
            try:
                self = cls._process[sid]
            except KeyError:
                return
            #TODO(robnagler) will this happen?
            if self.in_kill:
                return
            self.in_kill = True
        pkdp('Killing: pid={} sid={}', self.pid, self.sid)
        sig = signal.SIGTERM
        for i in range(3):
            try:
                os.kill(self.pid, sig)
                time.sleep(1)
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid == self.pid:
                    pkdp('waitpid: pid={} status={}', pid, status)
                    break
                sig = signal.SIGKILL
            except OSError:
                # Already reaped(?)
                break
        with cls._lock:
            self.in_kill = False
            try:
                del self._process[self.sid]
                pkdp('Deleted: sid={}', self.sid)
            except KeyError:
                pass

    @classmethod
    def sigchld_handler(cls, signum=None, frame=None):
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            pkdp('waitpid: pid={} status={}', pid, status)
            with cls._lock:
                for self in cls._process.values():
                    if self.pid == pid:
                        del self._process[self.sid]
                        pkdp('Deleted: sid={}', self.sid)
                        return
        except OSError as e:
            if e.errno != errno.ECHILD:
                pkdp('waitpid OSError: {} ({})', e.strerror, e.errno)
                # Fall through. Not much to do here

    def _create_daemon(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        try:
            pid = os.fork()
        except OSError as e:
            pkdp('fork OSError: {} ({})', e.strerror, e.errno)
            reraise
        if pid != 0:
            pkdp('Started: pid={} sid={} cmd={}', pid, self.sid, self.cmd)
            return pid
        try:
            os.chdir(str(self.run_dir))
            os.setsid()
            import resource
            maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            if (maxfd == resource.RLIM_INFINITY):
                maxfd = 1024
            for fd in range(0, maxfd):
                try:
                    os.close(fd)
                except OSError:
                    pass
            sys.stdin = open('background.log', 'a+')
            assert sys.stdin.fileno() == 0
            os.dup2(0, 1)
            sys.stdout = os.fdopen(1, 'a+')
            os.dup2(0, 2)
            sys.stderr = os.fdopen(2, 'a+')
            pkdp('Starting: cmd={}', self.cmd)
            sys.stderr.flush()
            try:
                os.execvp(self.cmd[0], self.cmd)
            finally:
                pkdp('execvp error: {} ({})', e.strerror, e.errno)
                sys.exit(1)
        except BaseException as e:
            err = open(str(self.run_dir.join('background.log')), 'a')
            err.write('Error starting daemon: {}\n'.format(e))
            err.close()
            reraise


class _Celery(object):

    # Map of sid to instance
    _task = {}

    # mutex for _task
    _lock = threading.Lock()

    def __init__(self, sid, run_dir, cmd):
        with self._lock:
            assert not sid in self._task, \
                'Simulation already running: sid={}'.format(sid)
            self.sid = sid
            self.cmd = cmd
            self.run_dir = run_dir
            self._task[sid] = self
            self.async_result = None
            # This command may blow up
            self.async_result = self._start_task()

    @classmethod
    def is_running(cls, sid):
        with cls._lock:
            return cls._async_result(sid) is not None

    @classmethod
    def kill(cls, sid):
        from celery.exceptions import TimeoutError
        with cls._lock:
            res = cls._async_result(sid)
            if not res:
                return
            pkdp('Killing: tid={} sid={}', res.task_id, sid)
        try:
            res.revoke(terminate=True, wait=True, timeout=1, signal='SIGTERM')
        except TimeoutError as e:
            res.revoke(terminate=True, signal='SIGKILL')
        with cls._lock:
            try:
                del cls._task[sid]
                pkdp('Deleted: sid={}', sid)
            except KeyError:
                pass

    @classmethod
    def _async_result(cls, sid):
            try:
                self = cls._task[sid]
            except KeyError:
                return None
            res = self.async_result
            if not res or res.ready():
                del self._task[sid]
                return None
            return res

    def _start_task(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        from sirepo import celery_tasks
        return celery_tasks.start_simulation.apply_async([self.cmd[1], self.run_dir])


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
        self.background_simulation_id = ''

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


#: Replace with pkconfig
_cfg = pkcollections.OrderedMapping(
    session=pkcollections.OrderedMapping(
        secure=os.getenv('SIREPO_SERVER_SESSION_SECURE', False),
        secret=os.getenv('SIREPO_SERVER_SESSION_SECRET', None),
        # Eventually {{ root_pkg }}_{{ channel }}
        key=os.getenv('SIREPO_SERVER_SESSION_KEY', 'sirepo_dev'),
    ),
    daemonizer=os.getenv('SIREPO_SERVER_JOB_QUEUE', 'Background'),
)

# This would a be a parser
_cfg.daemonizer = _cfg_daemonizer(_cfg.daemonizer)
_cfg.session.secret = _cfg_session_secret(_cfg.session.secret)
