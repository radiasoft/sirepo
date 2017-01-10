# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import runner
from sirepo import simulation_db
from sirepo.template import template_common
import beaker.middleware
import datetime
import flask
import flask.sessions
import glob
import os
import py.path
import re
import sirepo.template
import sys
import time
import werkzeug
import werkzeug.exceptions


#: where users live under db_dir
_BEAKER_DATA_DIR = 'beaker'

#: where users live under db_dir
_BEAKER_LOCK_DIR = 'lock'

#: What's the key in environ for the session
_ENVIRON_KEY_BEAKER = 'beaker.session'

#: Cache for _json_response_ok
_JSON_RESPONSE_OK = None

#: Callback url from OAUTH server
_OAUTH_AUTHORIZATION_CALLBACK_URL = '/<oauth_type>/oauth-authorized'

#: What is_running?
_RUN_STATES = ('pending', 'running')

#: Identifies the user in the Beaker session
_SESSION_KEY_USER = 'uid'

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:warning|exception|error): ([^\n]+)', flags=re.IGNORECASE)

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = 'sirepo_user'

#: WSGIApp instance (see `init_by_server`)
_wsgi_app = None

#: Flask app instance, must be bound globally
app = flask.Flask(
    __name__,
    static_folder=str(simulation_db.STATIC_FOLDER),
    template_folder=str(simulation_db.STATIC_FOLDER),
)
app.config.update(
    PROPAGATE_EXCEPTIONS=True,
)


def init(db_dir, uwsgi=None):
    """Initialize globals and populate simulation dir"""
    global _wsgi_app
    _wsgi_app = _WSGIApp(app, uwsgi)
    _BeakerSession().sirepo_init_app(app, py.path.local(db_dir))
    simulation_db.init_by_server(app, sys.modules[__name__])


@app.route(simulation_db.SCHEMA_COMMON['route']['copyNonSessionSimulation'], methods=('GET', 'POST'))
def app_copy_nonsession_simulation():
    req = _json_input()
    sim_type = req['simulationType']
    global_path = simulation_db.find_global_simulation(sim_type, req['simulationId'])
    if global_path:
        data = simulation_db.open_json_file(sim_type, os.path.join(global_path, simulation_db.SIMULATION_DATA_FILE))
        data['models']['simulation']['isExample'] = False
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
    data = simulation_db.read_simulation_json(sim_type, sid=req['simulationId'])
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
    data['models']['simulation']['isExample'] = False
    data['models']['simulation']['outOfSessionSimulationId'] = ''
    return _save_new_and_reply(sim_type, data)


@app.route(simulation_db.SCHEMA_COMMON['route']['deleteSimulation'], methods=('GET', 'POST'))
def app_delete_simulation():
    data = _parse_data_input()
    simulation_db.delete_simulation(data['simulationType'], data['simulationId'])
    return _json_response_ok()


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
    return _as_attachment(flask.make_response(content), content_type, filename)


@app.route(simulation_db.SCHEMA_COMMON['route']['downloadFile'], methods=('GET', 'POST'))
def app_download_file(simulation_type, simulation_id, filename):
    lib = simulation_db.simulation_lib_dir(simulation_type)
    p = lib.join(werkzeug.secure_filename(filename))
    return flask.send_file(str(p), as_attachment=True, attachment_filename=filename)


@app.route(simulation_db.SCHEMA_COMMON['route']['errorLogging'], methods=('GET', 'POST'))
def app_error_logging():
    ip = flask.request.remote_addr
    try:
        pkdlog(
            '{}: javascript error: {}',
            ip,
            simulation_db.generate_json(_json_input(), pretty=True),
        )
    except ValueError as e:
        pkdlog(
            '{}: error parsing javascript app_error: {} input={}',
            ip,
            e,
            flask.request.data.decode('unicode-escape'),
        )
    return _json_response_ok();


@app.route(simulation_db.SCHEMA_COMMON['route']['exportSimulation'], methods=('GET', 'POST'))
def app_export_simulation(simulation_type, simulation_id, filename):
    from sirepo import exporter
    p = exporter.create_zip(simulation_type, simulation_id)
    return flask.send_file(
        str(p),
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename=filename,
    )


@app.route('/favicon.ico')
def app_favicon():
    """Routes to favicon.ico file."""
    return flask.send_from_directory(
        str(simulation_db.STATIC_FOLDER.join('img')),
        'favicon.ico', mimetype='image/vnd.microsoft.icon'
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['listFiles'], methods=('GET', 'POST'))
def app_file_list(simulation_type, simulation_id, file_type):
    file_type = werkzeug.secure_filename(file_type)
    res = []
    exclude = None
    #TODO(pjm): use file prefixes for srw, currently assumes mirror is *.dat and others are *.zip
    if simulation_type == 'srw':
        template = sirepo.template.import_module(simulation_type)
        search = template.extensions_for_file_type(file_type)
        if file_type == 'sample':
            exclude = '_processed.tif'
    else:
        search = ['{}.*'.format(file_type)]
    d = simulation_db.simulation_lib_dir(simulation_type)
    for extension in search:
        for f in glob.glob(str(d.join(extension))):
            if exclude and re.search(exclude, f):
                continue
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
    if cfg.oauth_login:
        from sirepo import oauth
        oauth.set_default_state(logged_out_as_anonymous=True)
    redirect_uri = None
    # use the existing named simulation, or copy it from the examples
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
        if application_mode == 'default':
            redirect_uri = '/{}#/source/{}'.format(simulation_type, rows[0]['simulationId'])
        elif application_mode == 'lattice':
            redirect_uri = '/{}#/lattice/{}'.format(simulation_type, rows[0]['simulationId'])
        elif application_mode == 'wavefront' or application_mode == 'light-sources':
            redirect_uri = '/{}#/beamline/{}?application_mode={}'.format(
                simulation_type, rows[0]['simulationId'], application_mode)
        else:
            redirect_uri = '/{}#/source/{}?application_mode={}'.format(
                simulation_type, rows[0]['simulationId'], application_mode)
    if redirect_uri:
        return javascript_redirect(redirect_uri)
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
    new_simulation_data = _parse_data_input()
    sim_type = new_simulation_data['simulationType']
    data = simulation_db.default_data(sim_type)
    data['models']['simulation']['name'] = new_simulation_data['name']
    data['models']['simulation']['folder'] = new_simulation_data['folder']
    sirepo.template.import_module(sim_type).new_simulation(data, new_simulation_data)
    return _save_new_and_reply(sim_type, data)


@app.route(_OAUTH_AUTHORIZATION_CALLBACK_URL, methods=('GET', 'POST'))
def app_oauth_authorized(oauth_type):
    if cfg.oauth_login:
        from sirepo import oauth
        return oauth.authorized_callback(app, oauth_type)
    raise RuntimeError('OAUTH Login not configured')


@app.route(simulation_db.SCHEMA_COMMON['route']['oauthLogin'], methods=('GET', 'POST'))
def app_oauth_login(simulation_type, oauth_type):
    if cfg.oauth_login:
        from sirepo import oauth
        return oauth.authorize(simulation_type, app, oauth_type)
    raise RuntimeError('OAUTH Login not configured')


@app.route(simulation_db.SCHEMA_COMMON['route']['oauthLogout'], methods=('GET', 'POST'))
def app_oauth_logout(simulation_type):
    if cfg.oauth_login:
        from sirepo import oauth
        return oauth.logout(simulation_type)
    raise RuntimeError('OAUTH Login not configured')


@app.route(simulation_db.SCHEMA_COMMON['route']['pythonSource'])
def app_python_source(simulation_type, simulation_id, model):
    data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
    template = sirepo.template.import_module(data)
    return _as_attachment(
        flask.make_response(template.python_source_for_model(data, model)),
        'text/x-python',
        '{}.py'.format(data['models']['simulation']['name']),
    )


@app.route('/robots.txt')
def app_robots_txt():
    """Tell robots to go away"""
    return flask.Response(
        'User-agent: *\nDisallow: /\n',
        mimetype='text/plain',
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['root'])
def app_root(simulation_type):
    args = {}
    if cfg.oauth_login:
        from sirepo import oauth
        args = oauth.set_default_state()
    return flask.render_template(
        'html/index.html',
        version=simulation_db.app_version(),
        app_name=simulation_type,
        oauth_login=cfg.oauth_login,
        **args)


@app.route(simulation_db.SCHEMA_COMMON['route']['runCancel'], methods=('GET', 'POST'))
def app_run_cancel():
    data = _parse_data_input()
    jid = simulation_db.job_id(data)
    # TODO(robnagler) need to have a way of listing jobs
    # Don't bother with cache_hit check. We don't have any way of canceling
    # if the parameters don't match so for now, always kill.
    #TODO(robnagler) mutex required
    if cfg.job_queue.is_processing(jid):
        run_dir = simulation_db.simulation_run_dir(data)
        # Write first, since results are write once, and we want to
        # indicate the cancel instead of the termination error that
        # will happen as a result of the kill.
        simulation_db.write_result({'state': 'canceled'}, run_dir=run_dir)
        cfg.job_queue.kill(jid)
        # TODO(robnagler) should really be inside the template (t.cancel_simulation()?)
        # the last frame file may not be finished, remove it
        t = sirepo.template.import_module(data)
        t.remove_last_frame(run_dir)
    # Always true from the client's perspective
    return _json_response({'state': 'canceled'})


@app.route(simulation_db.SCHEMA_COMMON['route']['runSimulation'], methods=('GET', 'POST'))
def app_run_simulation():
    data = _parse_data_input(validate=True)
    res = _simulation_run_status(data, quiet=True)
    if (
        (
            not res['state'] in _RUN_STATES
            and (res['state'] != 'completed' or data.get('forceRun', False))
        ) or res.get('parametersChanged', True)
    ):
        try:
            _start_simulation(data)
        except runner.Collision:
            pkdlog('{}: runner.Collision, ignoring start', simulation_db.job_id(data))
        res = _simulation_run_status(data)
    return _json_response(res)


@app.route(simulation_db.SCHEMA_COMMON['route']['runStatus'], methods=('GET', 'POST'))
def app_run_status():
    data = _parse_data_input()
    return _json_response(_simulation_run_status(data))


@app.route(simulation_db.SCHEMA_COMMON['route']['saveSimulationData'], methods=('GET', 'POST'))
def app_save_simulation_data():
    data = _parse_data_input(validate=True)
    res = _validate_serial(data)
    if res:
        return res
    simulation_type = data['simulationType']
    data = simulation_db.save_simulation_json(
        simulation_type,
        sirepo.template.import_module(simulation_type).prepare_for_save(data),
    )
    return app_simulation_data(
        data['simulationType'],
        data['models']['simulation']['simulationId'],
        pretty=False,
    )


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationData'])
def app_simulation_data(simulation_type, simulation_id, pretty):
    #TODO(robnagler) need real type transforms for inputs
    pretty = bool(int(pretty))
    try:
        data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
        response = _json_response(
            sirepo.template.import_module(simulation_type).prepare_for_client(data),
            pretty=pretty,
        )
        if pretty:
            _as_attachment(
                response,
                app.config.get('JSONIFY_MIMETYPE', 'application/json'),
                '{}.json'.format(data['models']['simulation']['name']),
            )
    except simulation_db.CopyRedirect as e:
        response = _json_response(e.sr_response)
    _no_cache(response)
    return response


@app.route(simulation_db.SCHEMA_COMMON['route']['simulationFrame'])
def app_simulation_frame(frame_id):
    #TODO(robnagler) startTime is reportParametersHash; need version on URL and/or param names in URL
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    data = dict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data)
    data['report'] = template.get_animation_name(data)
    run_dir = simulation_db.simulation_run_dir(data)
    model_data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
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


SR_UNIT_ROUTE = '/ sr_unit'
SR_UNIT_TEST_IN_REQUEST = 'test_in_request'
@app.route(SR_UNIT_ROUTE, methods=('GET', 'POST'))
def app_sr_unit():
    getattr(app, 'test_in_request')()
    return ''


@app.route(simulation_db.SCHEMA_COMMON['route']['updateFolder'], methods=('GET', 'POST'))
def app_update_folder():
    #TODO(robnagler) Folder should have a serial, or should it be on data
    data = _parse_data_input()
    old_name = data['oldName']
    new_name = data['newName']
    for row in simulation_db.iterate_simulation_datafiles(data['simulationType'], _simulation_data):
        folder = row['models']['simulation']['folder']
        if folder.startswith(old_name):
            row['models']['simulation']['folder'] = re.sub(re.escape(old_name), new_name, folder, 1)
            simulation_db.save_simulation_json(data['simulationType'], row)
    return _json_response_ok()


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


def clear_session_user():
    """Remove the current user from the flask session.
    """
    if _SESSION_KEY_USER in flask.session:
        del flask.session[_SESSION_KEY_USER]


def javascript_redirect(redirect_uri):
    """Redirect using javascript for safari browser which doesn't support hash redirects.
    """
    return flask.render_template(
        'html/javascript-redirect.html',
        redirect_uri=redirect_uri
    )


@app.route('/')
@app.route('/light')
def light_landing_page():
    return flask.render_template(
        'html/sr-landing-page.html',
        version=simulation_db.app_version(),
    )


def session_user(*args, **kwargs):
    """Get/set the user from the Flask session

    With no positional arguments, is a getter. Else a setter.

    Args:
        user (str): if args[0], will set the user; else gets
        checked (bool): if kwargs['checked'], assert the user is truthy
        environ (dict): session environment to use instead of `flask.session`

    Returns:
        str: user id
    """
    environ = kwargs.get('environ', None)
    session = environ.get(_ENVIRON_KEY_BEAKER) if environ else flask.session
    if args:
        session[_SESSION_KEY_USER] = args[0]
        _wsgi_app.set_log_user(args[0])
    res = session.get(_SESSION_KEY_USER)
    if not res and kwargs.get('checked', True):
        raise KeyError(_SESSION_KEY_USER)
    return res


@app.route('/sr')
def sr_landing_page():
    return flask.redirect('/light')


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
        return request.environ[_ENVIRON_KEY_BEAKER]

    def save_session(self, *args, **kwargs):
        """Necessary to complete abstraction, but Beaker autosaves"""
        pass


class _WSGIApp(object):
    """Wraps Flask's wsgi_app for logging

    Args:
        app (Flask.app): Flask application being wrapped
        uwsgi (module): `uwsgi` module passed from ``uwsgi.py.jinja``
    """
    def __init__(self, app, uwsgi):
        self.app = app
        # Is None if called from sirepo.pkcli.service.http or FlaskClient
        self.uwsgi = uwsgi
        self.wsgi_app = app.wsgi_app
        app.wsgi_app = self

    def set_log_user(self, user):
        if self.uwsgi:
            log_user = 'li-' + user if user else '-'
            # Only works for uWSGI (service.uwsgi). For service.http,
            # werkzeug.serving.WSGIRequestHandler.log hardwires '%s - - [%s] %s\n',
            # and no point in overriding, since just for development.
            self.uwsgi.set_logvar(_UWSGI_LOG_KEY_USER, log_user)

    def __call__(self, environ, start_response):
        """An "app" called by uwsgi with requests.
        """
        self.set_log_user(session_user(checked=False, environ=environ))
        return self.wsgi_app(environ, start_response)


def _as_attachment(response, content_type, filename):
    response.mimetype = content_type
    response.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return response


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


def _json_input():
    req = flask.request
    if req.mimetype != 'application/json':
        pkdlog('{}: req.mimetype is not application/json', req.mimetype)
        raise werkzeug.Exceptions.BadRequest('expecting application/json')
    # Adapted from flask.wrappers.Request.get_json
    # We accept a request charset against the specification as
    # certain clients have been using this in the past.  This
    # fits our general approach of being nice in what we accept
    # and strict in what we send out.
    charset = req.mimetype_params.get('charset')
    data = req.get_data(cache=False)
    return simulation_db.json_load(data, encoding=charset)


def _json_response(value, pretty=False):
    """Generate JSON flask response

    Args:
        value (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        Response: flask response
    """
    return app.response_class(
        simulation_db.generate_json(value, pretty=pretty),
        mimetype=app.config.get('JSONIFY_MIMETYPE', 'application/json'),
    )


def _json_response_ok():
    """Generate state=ok JSON flask response

    Returns:
        Response: flask response
    """
    global _JSON_RESPONSE_OK
    if not _JSON_RESPONSE_OK:
        _JSON_RESPONSE_OK = _json_response({'state': 'ok'})
    return _JSON_RESPONSE_OK


def _mtime_or_now(path):
    """mtime for path if exists else time.time()

    Args:
        path (py.path):

    Returns:
        int: modification time
    """
    return int(path.mtime() if path.exists() else time.time())


def _no_cache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'


def _parse_data_input(validate=False):
    data = _json_input()
    return simulation_db.fixup_old_data(data)[0] if validate else data


def _save_new_and_reply(*args):
    data = simulation_db.save_new_simulation(*args)
    return app_simulation_data(
        data['simulationType'],
        data['models']['simulation']['simulationId'],
        pretty=False,
    )


def _simulation_error(err, *args, **kwargs):
    """Something unexpected went wrong.

    Parses ``err`` for error

    Args:
        err (str): exception or run_log
        quiet (bool): don't write errors to log
    Returns:
        dict: error response
    """
    if not kwargs.get('quiet'):
        pkdlog('{}', ': '.join([str(a) for a in args] + ['error', err]))
    m = re.search(_SUBPROCESS_ERROR_RE, str(err))
    if m:
        err = m.group(1)
        if re.search(r'error exit\(-15\)', err):
            err = 'Terminated'
    elif not pkconfig.channel_in_internal_test():
        err = 'unexpected error (see logs)'
    return {'state': 'error', 'error': err}


def _simulation_data(res, path, data):
    """Iterator function to return entire simulation data
    """
    res.append(data)


def _simulation_name(res, path, data):
    """Iterator function to return simulation name
    """
    res.append(data['models']['simulation']['name'])


def _simulation_run_status(data, quiet=False):
    """Look for simulation status and output

    Args:
        data (dict): request
        quiet (bool): don't write errors to log

    Returns:
        dict: status response
    """
    try:
        #TODO(robnagler): Lock
        rep = simulation_db.report_info(data)
        is_processing = cfg.job_queue.is_processing(rep.job_id)
        is_running = rep.job_status in _RUN_STATES
        res = {'state': rep.job_status}
        pkdc(
            '{}: is_processing={} is_running={} state={} cached_data={}',
            rep.job_id,
            is_processing,
            is_running,
            rep.job_status,
            bool(rep.cached_data),
        )
        if is_processing and not is_running:
            cfg.job_queue.race_condition_reap(rep.job_id)
            pkdc('{}: is_processing and not is_running', rep.job_id)
            is_processing = False
        if is_processing:
            if not rep.cached_data:
                return _simulation_error(
                    'input file not found, but job is running',
                    rep.input_file,
                )
        else:
            is_running = False
            if rep.run_dir.exists():
                res, err = simulation_db.read_result(rep.run_dir)
                if err:
                    return _simulation_error(err, 'error in read_result', rep.run_dir)
        if simulation_db.is_parallel(data):
            template = sirepo.template.import_module(data)
            new = template.background_percent_complete(
                rep.model_name,
                rep.run_dir,
                is_running,
                simulation_db.get_schema(data['simulationType']),
            )
            new.setdefault('percentComplete', 0.0)
            new.setdefault('frameCount', 0)
            res.update(new)
        res['parametersChanged'] = rep.parameters_changed
        if res['parametersChanged']:
            pkdlog(
                '{}: parametersChanged=True req_hash={} cached_hash={}',
                rep.job_id,
                rep.req_hash,
                rep.cached_hash,
            )
        #TODO(robnagler) verify serial number to see what's newer
        res.setdefault('startTime', _mtime_or_now(rep.input_file))
        res.setdefault('lastUpdateTime', _mtime_or_now(rep.run_dir))
        res.setdefault('elapsedTime', res['lastUpdateTime'] - res['startTime'])
        if is_processing:
            res['nextRequestSeconds'] = simulation_db.poll_seconds(rep.cached_data)
            res['nextRequest'] = {
                'report': rep.model_name,
                'reportParametersHash': rep.cached_hash,
                'simulationId': rep.cached_data['simulationId'],
                'simulationType': rep.cached_data['simulationType'],
            }
        pkdc(
            '{}: processing={} state={} cache_hit={} cached_hash={} data_hash={}',
            rep.job_id,
            is_processing,
            res['state'],
            rep.cache_hit,
            rep.cached_hash,
            rep.req_hash,
        )
    except Exception:
        return _simulation_error(pkdexc(), quiet=quiet)
    return res


def _start_simulation(data):
    """Setup and start the simulation.

    Args:
        data (dict): app data
    Returns:
        object: runner instance
    """
    data['simulationStatus'] = {
        'startTime': int(time.time()),
        'state': 'pending',
    }
    cfg.job_queue(data)


def _validate_serial(data):
    """Verify serial in data validates

    Args:
        data (dict): request with serial and possibly models

    Returns:
        object: None if all ok, or json response if invalid
    """
    res = simulation_db.validate_serial(data)
    if not res:
        return None
    return _json_response({
        'state': 'error',
        'error': 'invalidSerial',
        'simulationData': res,
    })


cfg = pkconfig.init(
    beaker_session=dict(
        key=('sirepo_{PYKERN_PKCONFIG_CHANNEL}', str, 'Beaker: Name of the cookie key used to save the session under'),
        secret=(None, _cfg_session_secret, 'Beaker: Used with the HMAC to ensure session integrity'),
        secure=(False, bool, 'Beaker: Whether or not the session cookie should be marked as secure'),
    ),
    job_queue=('Background', runner.cfg_job_queue, 'how to run long tasks: Celery or Background'),
    foreground_time_limit=(5 * 60, _cfg_time_limit, 'timeout for short (foreground) tasks'),
    oauth_login=(False, bool, 'OAUTH: enable login'),
)
