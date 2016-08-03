# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import beaker.middleware
import datetime
import errno
import flask
import flask.sessions
import glob
import json
import os
import py
import re
import signal
import sirepo.template
import subprocess
import sys
import threading
import time
import werkzeug
import werkzeug.exceptions


#: Cache of schemas keyed by app name
_SCHEMA_CACHE = {}

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:Warning|Exception|Error): ([^\n]+)')

#: where users live under db_dir
_BEAKER_DATA_DIR = 'beaker'

#: where users live under db_dir
_BEAKER_LOCK_DIR = 'lock'

#: What to exec (root_pkg)
_ROOT_CMD = 'sirepo'

#: Flask app instance, must be bound globally
app = None


class _BeakerSession(flask.sessions.SessionInterface):
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
        """Initialize cfg with db_dir and register self with Flask

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
        for k in cfg.beaker_session:
            sc['session.' + k] = cfg.beaker_session[k]
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
    static_folder=str(simulation_db.STATIC_FOLDER),
    template_folder=str(simulation_db.STATIC_FOLDER),
)


def init(db_dir):
    """Initialize globals and populate simulation dir"""
    _BeakerSession().sirepo_init_app(app, py.path.local(db_dir))
    simulation_db.init(app)


@app.route(simulation_db.SCHEMA_COMMON['route']['clearFrames'], methods=('GET', 'POST'))
def app_clear_frames():
    """Clear animation frames for the simulation."""
    data = _json_input()
    simulation_db.simulation_run_dir(data, remove_dir=True)
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['copyNonSessionSimulation'], methods=('GET', 'POST'))
def app_copy_nonsession_simulation():
    req = _json_input()
    simulation_type = req['simulationType']
    global_path = simulation_db.find_global_simulation(simulation_type, req['simulationId'])
    if global_path:
        data = simulation_db.open_json_file(simulation_type, os.path.join(global_path, simulation_db.SIMULATION_DATA_FILE))
        data['models']['simulation']['isExample'] = ''
        data['models']['simulation']['outOfSessionSimulationId'] = req['simulationId']
        res = _save_new_and_reply(simulation_type, data)
        sirepo.template.import_module(simulation_type).copy_related_files(data, global_path, str(simulation_db.simulation_dir(simulation_type, simulation_db.parse_sid(data))))
        return res
    werkzeug.exceptions.abort(404)


@app.route(simulation_db.SCHEMA_COMMON['route']['copySimulation'], methods=('GET', 'POST'))
def app_copy_simulation():
    """Takes the specified simulation and returns a newly named copy with the suffix (copy X)"""
    req = _json_input()
    simulation_type = req['simulationType']
    name = req['name'] if 'name' in req else None
    data = simulation_db.open_json_file(simulation_type, sid=req['simulationId'])
    if not name:
        base_name = data['models']['simulation']['name']
        names = simulation_db.iterate_simulation_datafiles(simulation_type, _simulation_name)
        count = 0
        while True:
            count += 1
            name = base_name + ' (copy{})'.format(' {}'.format(count) if count > 1 else '')
            if name in names and count < 100:
                continue
            break
    data['models']['simulation']['name'] = name
    data['models']['simulation']['isExample'] = ''
    data['models']['simulation']['outOfSessionSimulationId'] = ''
    return _save_new_and_reply(simulation_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['deleteSimulation'], methods=('GET', 'POST'))
def app_delete_simulation():
    data = _json_input()
    pkio.unchecked_remove(simulation_db.simulation_dir(data['simulationType'], data['simulationId']))
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['downloadDataFile'], methods=('GET', 'POST'))
def app_download_data_file(simulation_type, simulation_id, model, frame):
    data = {
        'simulationType': simulation_type,
        'simulationId': simulation_id,
    }
    frame = int(frame)
    template = sirepo.template.import_module(simulation_type)
    if frame >= 0:
        data['report'] = template.get_animation_name(data)
    else:
        data['report'] = model
    run_dir = simulation_db.simulation_run_dir(data)
    filename, content, content_type = template.get_data_file(run_dir, model, frame)
    response = flask.make_response(content)
    response.mimetype = content_type
    if content_type != 'text/plain':
        response.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return response


@app.route(simulation_db.SCHEMA_COMMON['route']['downloadFile'], methods=('GET', 'POST'))
def app_download_file(simulation_type, simulation_id, filename):
    lib = simulation_db.simulation_lib_dir(simulation_type)
    p = lib.join(werkzeug.secure_filename(filename))
    return flask.send_file(str(p))


@app.route(simulation_db.SCHEMA_COMMON['route']['errorLogging'], methods=('GET', 'POST'))
def app_error_logging():
    try:
        print('javascript error: {}'.format(_json_input()))
    except ValueError:
        print('unparsable javascript error: {}'.format(
            flask.request.data.decode('unicode-escape')))
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['listFiles'], methods=('GET', 'POST'))
def app_file_list(simulation_type, simulation_id, file_type):
    file_type = werkzeug.secure_filename(file_type)
    res = []
    #TODO(pjm): use file prefixes for srw, currently assumes mirror is *.dat and others are *.zip
    if simulation_type == 'srw':
        search = '*.dat' if file_type == 'mirror' else '*.zip'
    else:
        search = '{}.*'.format(file_type)
    d = simulation_db.simulation_lib_dir(simulation_type)
    for f in glob.glob(str(d.join(search))):
        if os.path.isfile(f):
            filename = os.path.basename(f)
            if not simulation_type == 'srw':
                # strip the file_type prefix
                filename = filename[len(file_type) + 1:]
            res.append(filename)
    res.sort()
    return json.dumps(res)


@app.route(simulation_db.SCHEMA_COMMON['route']['findByName'], methods=('GET', 'POST'))
def app_find_by_name(simulation_type, application_mode, simulation_name):
    redirect_uri = None
    if application_mode == 'light-sources':
        show_item_id = None
        # for light-sources application mode, the simulation_name is the facility
        # copy all new examples into the session
        examples = sorted(
            simulation_db.examples(simulation_type),
            key=lambda row: row['models']['simulation']['folder'],
        )
        for s in examples:
            if s['models']['simulation']['facility'] == simulation_name:
                rows = simulation_db.iterate_simulation_datafiles(simulation_type, simulation_db.process_simulation_list, {
                    'simulation.name': s['models']['simulation']['name'],
                })
                if len(rows):
                    id = rows[0]['simulationId']
                else:
                    type, id = simulation_db.save_new_example(simulation_type, s)
                if not show_item_id:
                    show_item_id = id
        redirect_uri = '/{}#/simulations?simulation.facility={}&application_mode={}&show_item_id={}'.format(
            simulation_type, flask.escape(simulation_name), application_mode, show_item_id)
    else:
        # otherwise use the existing named simulation, or copy it from the examples
        rows = simulation_db.iterate_simulation_datafiles(simulation_type, simulation_db.process_simulation_list, {
            'simulation.name': simulation_name,
        })
        if len(rows) == 0:
            for s in simulation_db.examples(simulation_type):
                if s['models']['simulation']['name'] == simulation_name:
                    simulation_db.save_new_example(simulation_type, s)
                    rows = simulation_db.iterate_simulation_datafiles(simulation_type, simulation_db.process_simulation_list, {
                        'simulation.name': simulation_name,
                    })
                    break
        if len(rows):
            if application_mode == 'wavefront':
                redirect_uri = '/{}#/beamline/{}?application_mode={}'.format(
                    simulation_type, rows[0]['simulationId'], application_mode)
            else:
                redirect_uri = '/{}#/source/{}?application_mode={}'.format(
                    simulation_type, rows[0]['simulationId'], application_mode)

    if redirect_uri:
        # redirect using javascript for safari browser which doesn't support hash redirects
        return flask.render_template(
            'html/javascript-redirect.html',
            redirect_uri=redirect_uri
        )
    werkzeug.exceptions.abort(404)


@app.route(simulation_db.SCHEMA_COMMON['route']['getApplicationData'], methods=('GET', 'POST'))
def app_get_application_data():
    data = _json_input()
    return flask.jsonify(sirepo.template.import_module(data['simulationType']).get_application_data(data))


@app.route(simulation_db.SCHEMA_COMMON['route']['importFile'], methods=('GET', 'POST'))
def app_import_file(simulation_type):
    template = sirepo.template.import_module(simulation_type)
    error, data = template.import_file(flask.request, simulation_db.simulation_lib_dir(simulation_type), simulation_db.tmp_dir())
    if error:
        return flask.jsonify({'error': error})
    data['models']['simulation']['folder'] = flask.request.form['folder']
    return _save_new_and_reply(simulation_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['newSimulation'], methods=('GET', 'POST'))
def app_new_simulation():
    new_simulation_data = _json_input()
    simulation_type = new_simulation_data['simulationType']
    data = simulation_db.open_json_file(
        simulation_type,
        simulation_db.STATIC_FOLDER.join('json', '{}-default{}'.format(simulation_type, simulation_db.JSON_SUFFIX)),
    )
    data['models']['simulation']['name'] = new_simulation_data['name']
    data['models']['simulation']['folder'] = new_simulation_data['folder']
    sirepo.template.import_module(simulation_type).new_simulation(data, new_simulation_data)
    return _save_new_and_reply(simulation_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['pythonSource'])
def app_python_source(simulation_type, simulation_id):
    data = simulation_db.open_json_file(simulation_type, sid=simulation_id)
    template = sirepo.template.import_module(simulation_type)
    # ensure the whole source gets generated, not up to the last watchpoint report
    last_watchpoint = None
    if 'beamline' in data['models']:
        for item in reversed(data['models']['beamline']):
            if item['type'] == 'watch':
                last_watchpoint = 'watchpointReport{}'.format(item['id'])
                break
            if last_watchpoint:
                data['report'] = last_watchpoint
    return flask.Response(
        '{}{}'.format(
            template.generate_parameters_file(data, _schema_cache(simulation_type), run_async=True),
            template.run_all_text(data) if simulation_type == 'srw' else template.run_all_text()),
        mimetype='text/plain',
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['root'])
def app_root(simulation_type):
    return flask.render_template(
        'html/index.html',
        version=simulation_db.SCHEMA_COMMON['version'],
        app_name=simulation_type,
    )


@app.route('/favicon.ico')
def app_route_favicon():
    """Routes to favicon.ico file."""
    return flask.send_from_directory(
        str(simulation_db.STATIC_FOLDER.join('img')),
        'favicon.ico', mimetype='image/vnd.microsoft.icon'
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['runSimulation'], methods=('GET', 'POST'))
def app_run():
    data = _json_input()
    run_dir = simulation_db.simulation_run_dir(data)
    res = _cached_simulation_results(run_dir, data)

    if not res:
        simulation = _start_simulation(data)
        err = simulation.run_and_read()
        if err:
            sid = simulation_db.parse_sid(data)
            pkdp('error: sid={}, dir={}, out={}', sid, run_dir, err)
            return flask.jsonify({
                'error': _error_text(err),
                'simulationId': sid,
            })
        res = simulation_db.read_json(run_dir.join(template_common.OUTPUT_BASE_NAME))
        res['report'] = str(run_dir.basename)
        res['duration'] = simulation.duration
        pkdp('report: {}, duration: {} seconds', res['report'], res['duration'])
    return flask.jsonify(res)


@app.route(simulation_db.SCHEMA_COMMON['route']['runBackground'], methods=('GET', 'POST'))
def app_run_background():
    data = _json_input()
    sid = simulation_db.parse_sid(data)
    #TODO(robnagler) race condition. Need to lock the simulation
    if cfg.job_queue.is_running(_job_id(sid, data['report'])):
        #TODO(robnagler) return error to user if in different window
        pkdp('ignoring second call to runBackground: {}'.format(sid))
        return '{}'
    status = data['models']['simulationStatus'][data['report']] = {}
    status['state'] = 'running'
    status['startTime'] = int(time.time())
    _start_simulation(data, run_async=True)
    return flask.jsonify({
        'state': status['state'],
        'startTime': status['startTime'],
    })


@app.route(simulation_db.SCHEMA_COMMON['route']['runCancel'], methods=('GET', 'POST'))
def app_run_cancel():
    data = _json_input()
    if data['report'] in data['models']['simulationStatus']:
        data['models']['simulationStatus'][data['report']]['state'] = 'canceled'
    simulation_type = data['simulationType']
    simulation_db.save_simulation_json(simulation_type, data)
    cfg.job_queue.kill(_job_id(simulation_db.parse_sid(data), data['report']))
    # the last frame file may not be finished, remove it
    t = sirepo.template.import_module(simulation_type)
    t.remove_last_frame(simulation_db.simulation_run_dir(data))
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['runStatus'], methods=('GET', 'POST'))
def app_run_status():
    data = _json_input()
    sid = simulation_db.parse_sid(data)
    simulation_type = data['simulationType']
    template = sirepo.template.import_module(simulation_type)
    run_dir = simulation_db.simulation_run_dir(data)

    if cfg.job_queue.is_running(_job_id(sid, data['report'])):
        completion = template.background_percent_complete(data['report'], run_dir, True, _schema_cache(simulation_type))
        state = 'running'
    else:
        report = data['report']
        data = simulation_db.open_json_file(simulation_type, sid=sid)
        data['report'] = report
        if report not in data['models']['simulationStatus']:
            data['models']['simulationStatus'][report] = {
                'state': 'initial',
            }
        state = data['models']['simulationStatus'][report]['state']
        completion = template.background_percent_complete(data['report'], run_dir, False, _schema_cache(simulation_type))
        if state == 'running':
            if completion['percent_complete'] >= 100:
                state = 'completed'
            else:
                state = 'canceled'
            data['models']['simulationStatus'][report]['state'] = state
            simulation_db.save_simulation_json(data['simulationType'], data)

    frame_id = ''
    elapsed_time = ''
    if 'last_update_time' in completion and 'start_time' in completion:
        frame_id = completion['last_update_time']
        elapsed_time = int(frame_id) - int(completion['start_time'])

    return flask.jsonify({
        'state': completion['state'] if 'state' in completion else state,
        'percentComplete': completion['percent_complete'],
        'frameCount': completion['frame_count'],
        'frameId': frame_id,
        'elapsedTime': elapsed_time,
        'outputInfo': completion['output_info'] if 'output_info' in completion else None,
        'errors': completion['errors'] if 'errors' in completion else None,
    })


@app.route(simulation_db.SCHEMA_COMMON['route']['saveSimulationData'], methods=('GET', 'POST'))
def app_save_simulation_data():
    data = _json_input()
    simulation_db.save_simulation_json(data['simulationType'], data)
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationData'])
def app_simulation_data(simulation_type, simulation_id):
    response = flask.jsonify(simulation_db.open_json_file(simulation_type, sid=simulation_id))
    _no_cache(response)
    return response


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationFrame'])
def app_simulation_frame(frame_id):
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    data = dict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data['simulationType'])
    data['report'] = template.get_animation_name(data)
    run_dir = simulation_db.simulation_run_dir(data)
    model_data = simulation_db.open_json_file(data['simulationType'], sid=data['simulationId'])
    response = flask.jsonify(template.get_simulation_frame(run_dir, data, model_data))

    if template.WANT_BROWSER_FRAME_CACHE:
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(365)
        response.headers['Cache-Control'] = 'public, max-age=31536000'
        response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    else:
        _no_cache(response)
    return response


@app.route(simulation_db.SCHEMA_COMMON['route']['listSimulations'], methods=('GET', 'POST'))
def app_simulation_list():
    data = _json_input()
    simulation_type = data['simulationType']
    search = data['search'] if 'search' in data else None
    simulation_db.verify_app_directory(simulation_type)
    return json.dumps(
        sorted(
            simulation_db.iterate_simulation_datafiles(simulation_type, simulation_db.process_simulation_list, search),
            key=lambda row: row['name'],
        )
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationSchema'], methods=('GET', 'POST'))
def app_simulation_schema():
    sim_type = flask.request.form['simulationType']
    return flask.jsonify(_schema_cache(sim_type))


@app.route(simulation_db.SCHEMA_COMMON['route']['updateFolder'], methods=('GET', 'POST'))
def app_update_folder():
    data = _json_input()
    old_name = data['oldName']
    new_name = data['newName']
    for row in simulation_db.iterate_simulation_datafiles(data['simulationType'], _simulation_data):
        folder = row['models']['simulation']['folder']
        if folder.startswith(old_name):
            row['models']['simulation']['folder'] = re.sub(re.escape(old_name), new_name, folder, 1)
            simulation_db.save_simulation_json(data['simulationType'], row)
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['uploadFile'], methods=('GET', 'POST'))
def app_upload_file(simulation_type, simulation_id, file_type):
    f = flask.request.files['file']
    lib = simulation_db.simulation_lib_dir(simulation_type)
    template = sirepo.template.import_module(simulation_type)
    filename = werkzeug.secure_filename(f.filename)
    if simulation_type == 'srw':
        p = lib.join(filename)
    else:
        p = lib.join(werkzeug.secure_filename('{}.{}'.format(file_type, filename)))
    err = None
    if p.check():
        err = 'file exists: {}'.format(filename)
    if not err:
        f.save(str(p))
        err = template.validate_file(file_type, str(p))
        if err:
            pkio.unchecked_remove(p)
    if err:
        return flask.jsonify({
            'error': err,
            'filename': filename,
            'fileType': file_type,
            'simulationId': simulation_id,
        })
    return flask.jsonify({
        'filename': filename,
        'fileType': file_type,
        'simulationId': simulation_id,
    })


@app.route('/light')
def light_landing_page():
    return flask.render_template(
        'html/sr-landing-page.html',
        version=simulation_db.SCHEMA_COMMON['version'],
    )


@app.route('/sr')
def sr_landing_page():
    return flask.redirect('/light')


def _cached_simulation_results(run_dir, data):
    if not run_dir.check():
        return False
    try:
        old_data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        template = sirepo.template.import_module(data['simulationType'])
        if template.is_cache_valid(data, old_data):
            return simulation_db.read_json(run_dir.join(template_common.OUTPUT_BASE_NAME))
    except IOError as e:
        pass
    except Exception as e:
        # log non-IOErrors
        print('exception during _cached_simulation_available(): {}'.format(e))
    return False


def _cfg_job_queue(value):
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
        raise AssertionError('{}: unknown job_queue'.format(value))


@pkconfig.parse_none
def _cfg_session_secret(value):
    """Reads file specified as config value"""
    if not value:
        return 'dev dummy secret'
    with open(value) as f:
        return f.read()


def _cfg_time_limit(value):
    """Sets timeout in seconds"""
    v = int(value)
    assert v > 0
    return v


def _error_text(err):
    """Parses error from subprocess"""
    m = re.search(_SUBPROCESS_ERROR_RE, err)
    if m:
        return m.group(1)
    return 'a system error occurred'


def _job_id(sid, model_name):
    return '{}-{}'.format(sid, model_name)


def _json_input():
    return flask.request.get_json(cache=False)


def _no_cache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'


def _save_new_and_reply(*args):
    simulation_type, sid = simulation_db.save_new_simulation(*args)
    return app_simulation_data(simulation_type, sid)


def _schema_cache(sim_type):
    if sim_type in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[sim_type]
    with open(str(simulation_db.STATIC_FOLDER.join('json/{}-schema{}'.format(sim_type, simulation_db.JSON_SUFFIX)))) as f:
        schema = json.load(f)
    schema.update(simulation_db.SCHEMA_COMMON)
    schema['simulationType'] = sim_type
    _SCHEMA_CACHE[sim_type] = schema
    return schema


def _simulation_data(res, path, data):
    """Iterator function to return entire simulation data
    """
    res.append(data)


def _simulation_name(res, path, data):
    """Iterator function to return simulation name
    """
    res.append(data['models']['simulation']['name'])


def _start_simulation(data, run_async=False):
    """Setup and start the simulation.

    Args:
        data (dict): app data
        run_async (bool): run-background or run

    Returns:
        object: _Command or daemon instance
    """
    run_dir = simulation_db.simulation_run_dir(data, remove_dir=True)
    pkio.mkdir_parent(run_dir)
    #TODO(robnagler) create a lock_dir -- what node/pid/thread to use?
    #   probably can only do with celery.
    simulation_type = data['simulationType']
    sid = simulation_db.parse_sid(data)
    data = simulation_db.fixup_old_data(simulation_type, data)
    assert simulation_type in simulation_db.SIMULATION_TYPES, \
        '{}: invalid simulation type'.format(simulation_type)
    template = sirepo.template.import_module(simulation_type)
    for d in simulation_db.simulation_dir(simulation_type, sid), simulation_db.simulation_lib_dir(simulation_type):
        for f in glob.glob(str(d.join('*.*'))):
            if os.path.isfile(f):
                py.path.local(f).copy(run_dir)
    template.prepare_aux_files(run_dir, data)
    simulation_db.save_simulation_json(simulation_type, data)
    simulation_db.write_json(run_dir.join(template_common.INPUT_BASE_NAME), data)
    template.write_parameters(
        data, _schema_cache(simulation_type), run_dir=run_dir, run_async=run_async)
    cmd = [_ROOT_CMD, simulation_type] \
        + ['run-background' if run_async else 'run'] + [str(run_dir)]
    if run_async:
        return cfg.job_queue(_job_id(sid, data['report']), run_dir, cmd)
    return _Command(cmd, cfg.foreground_time_limit)


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
        self.duration = 0.0

    def run(self):
        start_time = time.time()
        self.process = subprocess.Popen(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.out = self.process.communicate()[0]
        self.duration = time.time() - start_time

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


cfg = pkconfig.init(
    beaker_session=dict(
        key=('sirepo_{PYKERN_PKCONFIG_CHANNEL}', str, 'Beaker: Name of the cookie key used to save the session under'),
        secret=(None, _cfg_session_secret, 'Beaker: Used with the HMAC to ensure session integrity'),
        secure=(False, bool, 'Beaker: Whether or not the session cookie should be marked as secure'),
    ),
    job_queue=('Background', _cfg_job_queue, 'how to run long tasks: Celery or Background'),
    foreground_time_limit=(5 * 60, _cfg_time_limit, 'timeout for short (foreground) tasks'),
)
