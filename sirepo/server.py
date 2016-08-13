# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import beaker.middleware
import copy
import datetime
import errno
import flask
import flask.sessions
import glob
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


#: Flask app instance, must be bound globally
app = None

#: where users live under db_dir
_BEAKER_DATA_DIR = 'beaker'

#: where users live under db_dir
_BEAKER_LOCK_DIR = 'lock'

#: Empty response
_EMPTY_JSON_RESPONSE = '{}'

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:Warning|Exception|Error): ([^\n]+)')


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
    data = _parse_data_input()
    simulation_db.simulation_run_dir(data, remove_dir=True)
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['copyNonSessionSimulation'], methods=('GET', 'POST'))
def app_copy_nonsession_simulation():
    req = _json_input()
    sim_type = req['simulationType']
    global_path = simulation_db.find_global_simulation(sim_type, req['simulationId'])
    if global_path:
        data = simulation_db.open_json_file(sim_type, os.path.join(global_path, simulation_db.SIMULATION_DATA_FILE))
        data['models']['simulation']['isExample'] = ''
        data['models']['simulation']['outOfSessionSimulationId'] = req['simulationId']
        res = _save_new_and_reply(sim_type, data)
        sirepo.template.import_module(data).copy_related_files(data, global_path, str(simulation_db.simulation_dir(sim_type, simulation_db.parse_sid(data))))
        return res
    werkzeug.exceptions.abort(404)


@app.route(simulation_db.SCHEMA_COMMON['route']['copySimulation'], methods=('GET', 'POST'))
def app_copy_simulation():
    """Takes the specified simulation and returns a newly named copy with the suffix (copy X)"""
    req = _json_input()
    sim_type = req['simulationType']
    name = req['name'] if 'name' in req else None
    data = simulation_db.open_json_file(sim_type, sid=req['simulationId'])
    if not name:
        base_name = data['models']['simulation']['name']
        names = simulation_db.iterate_simulation_datafiles(sim_type, _simulation_name)
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
    return _save_new_and_reply(sim_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['deleteSimulation'], methods=('GET', 'POST'))
def app_delete_simulation():
    data = _parse_data_input()
    pkio.unchecked_remove(simulation_db.simulation_dir(data['simulationType'], data['simulationId']))
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['downloadDataFile'], methods=('GET', 'POST'))
def app_download_data_file(simulation_type, simulation_id, model, frame):
    data = {
        'simulationType': simulation_type,
        'simulationId': simulation_id,
        'modelName': model,
    }
    frame = int(frame)
    template = sirepo.template.import_module(data)
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
    ip = flask.request.remote_addr
    try:
        pkdp('{}: javascript app_error: {}', ip, _json_input())
    except ValueError as e:
        pkdp('{}: error parsing javascript app_error: {} input={}', ip, e, flask.request.data.decode('unicode-escape')))
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
    return _json_response(res)


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
    data = _parse_data_input()
    return _json_response(sirepo.template.import_module(data).get_application_data(data))


@app.route(simulation_db.SCHEMA_COMMON['route']['importFile'], methods=('GET', 'POST'))
def app_import_file(simulation_type):
    template = sirepo.template.import_module(simulation_type)
    error, data = template.import_file(flask.request, simulation_db.simulation_lib_dir(simulation_type), simulation_db.tmp_dir())
    if error:
        return _json_response({'error': error})
    data['models']['simulation']['folder'] = flask.request.form['folder']
    return _save_new_and_reply(simulation_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['newSimulation'], methods=('GET', 'POST'))
def app_new_simulation():
    new_simulation_data = _parse_data_input(validate=True)
    sim_type = new_simulation_data['simulationType']
    data = simulation_db.open_json_file(
        sim_type,
        simulation_db.STATIC_FOLDER.join('json', '{}-default{}'.format(sim_type, simulation_db.JSON_SUFFIX)),
    )
    data['models']['simulation']['name'] = new_simulation_data['name']
    data['models']['simulation']['folder'] = new_simulation_data['folder']
    sirepo.template.import_module(data).new_simulation(data, new_simulation_data)
    return _save_new_and_reply(sim_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['pythonSource'])
def app_python_source(simulation_type, simulation_id):
    data = simulation_db.open_json_file(simulation_type, sid=simulation_id)
    template = sirepo.template.import_module(data)
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
            template.generate_parameters_file(data, simulation_db.get_schema(simulation_type), is_parallel=True),
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

@app.route(simulation_db.SCHEMA_COMMON['route']['zrunCancel'], methods=('GET', 'POST'))
def app_zrun_cancel():
    data = _parse_data_input()
    cache_data = _cached_simulation(data)
    data['state'] = 'canceled'
    if not cache_data:
        # Not our job or not run
        return _json_response(data)
    jid = _job_id(data)
    if not cfg.job_queue.is_running(jid):
        # Already dead
        return _json_response(data)
    pkdp('{}: canceling', jid)
    # TODO(robnagler) I think it is a mistake to write data. Too many
    # race conditions. Can't really trust the state anyway.
    cfg.job_queue.kill(jid)
    # TODO(robnagler) should really be inside the template (t.cancel_simulation()?)
    # the last frame file may not be finished, remove it
    t = sirepo.template.import_module(data)
    t.remove_last_frame(simulation_db.simulation_run_dir(data))
    return _json_response(data)


@app.route(simulation_db.SCHEMA_COMMON['route']['zrunSimulation'], methods=('GET', 'POST'))
def app_zrun_simulation():
    data = _parse_data_input(validate=True)
    cache_data = _cached_simulation(data)
    if cache_data:
        data = cache_data
        res = _simulation_run_result(data)
        # If not completed, just fall through and rerun
        if res['state'] == 'completed':
            return _json_response(res)
    #TODO(robnagler) race condition. Neaed to lock the simulation
    jid = _job_id(data)
    if cfg.job_queue.is_running(jid):
        #TODO(robnagler) return error to user if in different window
        pkdp('{}: ignoring second call to runBackground', jid)
        #TODO: reportParametersHash collision
    else:
        _start_simulation(data)
    status = data['simulationStatus']
    return _json_response({
        'pollSeconds': simulation_db.poll_seconds(data),
        'report': data['report'],
        'reportParametersHash': data['reportParametersHash'],
        'simulationId': simulation_db.parse_sid(data),
        'simulationType': data['simulationType'],
        'startTime': status['startTime'],
        'state': status['state'],
    })


@app.route(simulation_db.SCHEMA_COMMON['route']['zrunResult'], methods=('GET', 'POST'))
def app_zrun_result():
    return _json_response(_simulation_run_result(_parse_data_input()))


@app.route(simulation_db.SCHEMA_COMMON['route']['runStatus'], methods=('GET', 'POST'))
def app_run_status():
    data = _parse_data_input()
    sim_type = data['simulationType']
    sid = simulation_db.parse_sid(data)
    report = data['report']
    is_running = cfg.job_queue.is_running(_job_id(data))
    #TODO(robnagler) need to refresh here the data if the cache is a miss and running
    try:
        cached_data = _cached_simulation(data)
    except KeyError:
        #TODO(robnagler) REMOVE once clients are up to date (need to force client refresh)
        cached_data = None
        pkdp('out of date client: {}', flask.request.headers)
#   if cached_data:
#        data = cached_data
#    else:
#        # data = simulation_db.open_json_file(sim_type, sid=sid)
#        old = simulation_db.open_json_file(sim_type, sid=sid)
#        old.update(data)
#        data = old
#        if is_running:
#            #TODO(robnagler) not our job
#            pass
    run_dir = simulation_db.simulation_run_dir(data)
    template = sirepo.template.import_module(data)
    schema = simulation_db.get_schema(sim_type)
    new = template.background_percent_complete(report, run_dir, is_running, schema)
    #TODO(robnagler) Not the right way. Should always find in the cache or return
    # the report hash with a note that may not be the right values.
    new.setdefault('startTime', int(time.time()))
    new.setdefault('lastUpdateTime', int(time.time()))
    new.setdefault('percentComplete', 0.0)
    #TODO(robnagler) merge
    new.setdefault('frameCount', 0)
    new.setdefault('errors', None)
    new.setdefault('pollSeconds', simulation_db.poll_seconds(data))
    if is_running:
        new['state'] = 'running'
    else:
        # TODO(robnagler) this should be "aborted", b/c we don't know what's
        # going on.
        new.setdefault('state', 'canceled')
        if new['state'] == 'running':
            new['state'] = 'completed' if new['percentComplete'] >= 100 else 'canceled'
    status = data.setdefault('simulationStatus', {})
    status.update(new)
    return _json_response(_simulation_run_status(data, status))


@app.route(simulation_db.SCHEMA_COMMON['route']['saveSimulationData'], methods=('GET', 'POST'))
def app_save_simulation_data():
    data = _parse_data_input(validate=True)
    simulation_db.save_simulation_json(data['simulationType'], data)
    return '{}'


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationData'])
def app_simulation_data(simulation_type, simulation_id):
    response = _json_response(
        sirepo.template.import_module(simulation_type).prepare_for_client(data),
    )
    _no_cache(response)
    return response


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationFrame'])
def app_simulation_frame(frame_id):
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    data = dict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data)
    data['report'] = template.get_animation_name(data)
    run_dir = simulation_db.simulation_run_dir(data)
    model_data = simulation_db.open_json_file(data['simulationType'], sid=data['simulationId'])
    response = _json_response(template.get_simulation_frame(run_dir, data, model_data))

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
    data = _parse_data_input()
    sim_type = data['simulationType']
    search = data['search'] if 'search' in data else None
    simulation_db.verify_app_directory(sim_type)
    return _json_response(
        sorted(
            simulation_db.iterate_simulation_datafiles(sim_type, simulation_db.process_simulation_list, search),
            key=lambda row: row['name'],
        )
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationSchema'], methods=('GET', 'POST'))
def app_simulation_schema():
    sim_type = flask.request.form['simulationType']
    return _json_response(simulation_db.get_schema(sim_type))


@app.route(simulation_db.SCHEMA_COMMON['route']['updateFolder'], methods=('GET', 'POST'))
def app_update_folder():
    data = _parse_data_input()
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
        return _json_response({
            'error': err,
            'filename': filename,
            'fileType': file_type,
            'simulationId': simulation_id,
        })
    return _json_response({
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


def _cached_simulation(data):
    # Updates data['reportParametersHash']
    req_hash = template_common.report_parameters_hash(data)
    run_dir = simulation_db.simulation_run_dir(data)
    if not run_dir.check():
        return None
    #TODO(robnagler) Lock
    try:
        cache_data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        cache_hash = template_common.report_parameters_hash(cache_data)
        if req_hash == cache_hash:
            return cache_data
    except IOError as e:
        pkdp('{}: ignore IOError: {} errno=', run_dir, e)
    except Exception as e:
        pkdp('{}: ignore other error: {}', run_dir, str(e))
    return None


def _cfg_job_queue(value):
    """Converts string to class"""
    if isinstance(value, (_Celery, _Background)):
        # Already initialized but may call initializer with original object
        return value
    if value == 'Celery':
        from sirepo import celery_tasks
        try:
            if not celery_tasks.celery.control.ping():
                pkdp('You need to start Celery:\ncelery worker -A sirepo.celery_tasks -l info -c 1')
                sys.exit(1)
        except Exception:
            pkdp('You need to start Rabbit:\ndocker run --rm --hostname rabbit --name rabbit -p 5672:5672 -p 15672:15672 rabbitmq')
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


def _job_id(data):
    """A Job is a simulation and report name

    Args:
        data (dict): extract sid and report
    Returns:
        str: unique name
    """
    return '{}-{}'.format(simulation_db.parse_sid(data), data['report'])


def _json_input():
    return simulation_db.parse_json(flask.request.get_json(cache=False))


def _json_response(value):
    return app.response_class(
        simulation_db.generate_json_response(value),
        mimetype=app.config.get('JSONIFY_MIMETYPE', 'application/json'),
    )


def _no_cache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'


def _parse_data_input(validate=False):
    data = _json_input()
    return simulation_db.fixup_old_data(data['simulationType'], data) if validate else data


def _save_new_and_reply(*args):
    sim_type, sid = simulation_db.save_new_simulation(*args)
    return app_simulation_data(sim_type, sid)


def _simulation_data(res, path, data):
    """Iterator function to return entire simulation data
    """
    res.append(data)


def _simulation_name(res, path, data):
    """Iterator function to return simulation name
    """
    res.append(data['models']['simulation']['name'])


def _simulation_run_result(data):
    #TODO(robnagler) cache result
    data = _parse_data_input()
    try:
        data = _cached_simulation(data)
    except KeyError:
        #TODO(robnagler) REMOVE once clients are up to date (need to force client refresh)
        pkdp('out of date client: {}', flask.request.headers)
    jid = _job_id(data)
    if cfg.job_queue.is_running(jid):
        return _simulation_run_status(data, {'state': 'running'})
    try:
        run_dir = simulation_db.simulation_run_dir(data)
        res = simulation_db.read_json(run_dir.join(template_common.OUTPUT_BASE_NAME))
        # TODO(robnagler) duration isn't available for run foreground
        # res['duration'] = simulation.duration
        #TODO: reportParametersHash collision: state = 'collisionCompleted'
        res.setdefault('state', 'completed')
        return _simulation_run_status(data, res)
        #res['duration'] = 0.0
        #pkdp('{}: duration: {}s', jid, res['duration'])
    except Exception as e:
        pkdp('{}: simulation error: {}', jid, e)
        return _simulation_run_status(
            data, {'state': 'error', 'error': _error_text(str(e))})


def _simulation_run_status(data, other):
    try:
        status = data['simulationStatus']
    except KeyError:
        status = {
            'state': 'error',
            'error': 'invalid input; no simulationStatus (aborted run?)',
            'startTime': 0,
        }
    resp = copy.deepcopy(status)
    resp = {
        'pollSeconds': simulation_db.poll_seconds(data),
        'report': data['report'],
        'reportParametersHash': data['reportParametersHash'],
        'simulationId': simulation_db.parse_sid(data),
        'simulationType': data['simulationType'],
    }
    resp.setdefault('simulationType', data['simulationType'])
    resp.setdefault('simulationId', simulation_db.parse_sid(data))
    resp.setdefault('report', data['report'])
    resp.setdefault('reportParametersHash', data['reportParametersHash'])
    resp.update(other)
    return resp


def _start_simulation(data):
    """Setup and start the simulation.

    Args:
        data (dict): app data
    Returns:
        object: _Command or daemon instance
    """
    data['simulationStatus'] = {
        'startTime': int(time.time()),
        'state': 'running',
    }
    cmd, run_dir = simulation_db.prepare_simulation(data)
    return cfg.job_queue(_job_id(data), run_dir, cmd)


class _Background(object):

    # Map of jid to instance
    _process = {}

    # mutex for _process
    _lock = threading.Lock()

    def __init__(self, jid, run_dir, cmd):
        with self._lock:
            assert not jid in self._process, \
                'Simulation already running: jid={}'.format(jid)
            self.in_kill = False
            self.jid = jid
            self.cmd = cmd
            self.run_dir = run_dir
            self._process[jid] = self
            self.pid = None
            # This command may blow up
            self.pid = self._create_daemon()

    @classmethod
    def is_running(cls, jid):
        with cls._lock:
            try:
                self = cls._process[jid]
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
                del self._process[jid]
                return False
        return True

    @classmethod
    def kill(cls, jid):
        self = None
        with cls._lock:
            try:
                self = cls._process[jid]
            except KeyError:
                return
            #TODO(robnagler) will this happen?
            if self.in_kill:
                pkdp('{}: ASSUMPTION ERROR: self.in_kill is already set', jid)
                return
            self.in_kill = True
        pkdp('{}: stopping: pid={}', self.jid, self.pid)
        sig = signal.SIGTERM
        for i in range(3):
            try:
                os.kill(self.pid, sig)
                time.sleep(1)
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid == self.pid:
                    pkdp('{}: waitpid: status={}', pid, status)
                    break
                sig = signal.SIGKILL
            except OSError:
                # Already reaped(?)
                break
        with cls._lock:
            self.in_kill = False
            try:
                del self._process[self.jid]
                pkdp('{}: deleted', self.jid)
            except KeyError:
                pass

    @classmethod
    def sigchld_handler(cls, signum=None, frame=None):
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            pkdp('{}: waitpid: status={}', pid, status)
            with cls._lock:
                for self in cls._process.values():
                    if self.pid == pid:
                        del self._process[self.jid]
                        pkdp('{}: deleted', self.jid)
                        return
        except OSError as e:
            if e.errno != errno.ECHILD:
                pkdp('waitpid: OSError: {} errno={}', e.strerror, e.errno)
                # Fall through. Not much to do here

    def _create_daemon(self):
        """Detach a process from the controlling terminal and run it in the
        background as a daemon.
        """
        try:
            pid = os.fork()
        except OSError as e:
            pkdp('{}: fork OSError: {} errno={}', self.jid, e.strerror, e.errno)
            reraise
        if pid != 0:
            pkdp('{}: started: pid={} cmd={}', self.jid, pid, self.cmd)
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
            pkdp('{}: child will exec: {}', self.jid, self.cmd)
            sys.stderr.flush()
            try:
                os.execvp(self.cmd[0], self.cmd)
            finally:
                pkdp('{}: execvp error: {} errno={}', self.jid, e.strerror, e.errno)
                sys.exit(1)
        except BaseException as e:
            err = open(str(self.run_dir.join('background.log')), 'a')
            err.write('{}: error starting daemon: {}'.format(self.jid, e))
            err.close()
            reraise


class _Celery(object):

    # Map of jid to instance
    _task = {}

    # mutex for _task
    _lock = threading.Lock()

    def __init__(self, jid, run_dir, cmd):
        with self._lock:
            assert not jid in self._task, \
                'Simulation already running: jid={}'.format(jid)
            self.jid = jid
            self.cmd = cmd
            self.run_dir = run_dir
            self._task[jid] = self
            self.async_result = None
            # This command may blow up
            self.async_result = self._start_task()

    @classmethod
    def is_running(cls, jid):
        with cls._lock:
            return cls._async_result(jid) is not None

    @classmethod
    def kill(cls, jid):
        from celery.exceptions import TimeoutError
        with cls._lock:
            res = cls._async_result(jid)
            if not res:
                return
            pkdp('{}: killing: tid={} jid={}', jid, res.task_id)
        try:
            res.revoke(terminate=True, wait=True, timeout=1, signal='SIGTERM')
        except TimeoutError as e:
            res.revoke(terminate=True, signal='SIGKILL')
        with cls._lock:
            try:
                del cls._task[jid]
                pkdp('{}: deleted', jid)
            except KeyError:
                pass

    @classmethod
    def _async_result(cls, jid):
            try:
                self = cls._task[jid]
            except KeyError:
                return None
            res = self.async_result
            if not res or res.ready():
                del self._task[jid]
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

    def __init__(self, jid, cmd, timeout):
        super(_Command, self).__init__()
        # Daemon threads are stopped abruptly so won't hang the server
        self.daemon = True
        self.cmd = cmd
        self.timeout = timeout
        self.process = None
        self.out = ''
        self.background_simulation_id = ''
        self.duration = 0.0
        self.jid = jid

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
            pkdp('{}: timeout: cmd={}', self.jid, self.cmd)
            # Thread should exit, but make sure
            self.join(2)
            return self.out + '\nError: simulation took too long'
        except OSError as e:
            if e.errno != errno.ESRCH:
                pkdp('{}: OSError: {} errno={} cmd={}',
                     self.jid, e.strerror, e.errno, self.cmd)
                raise
        if self.process.returncode != 0:
            pkdp('{}: error: returncode={} cmd={}', self.jid, self.process.returncode, self.cmd)
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
