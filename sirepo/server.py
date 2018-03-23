# -*- coding: utf-8 -*-
u"""Flask routes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
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
import os.path
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

#: Relative to current directory only in test mode
_DEFAULT_DB_SUBDIR = 'run'

#: What's the key in environ for the session
_ENVIRON_KEY_BEAKER = 'beaker.session'

#: Cache for _json_response_ok
_JSON_RESPONSE_OK = None

#: class that py.path.local() returns
_PY_PATH_LOCAL_CLASS = type(py.path.local())

#: What is_running?
_RUN_STATES = ('pending', 'running')

#: Identifies the user in the Beaker session
_SESSION_KEY_USER = 'uid'

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:warning|exception|error): ([^\n]+?)(?:;|\n|$)', flags=re.IGNORECASE)

#: Identifies the user in uWSGI logging (read by uwsgi.yml.jinja)
_UWSGI_LOG_KEY_USER = 'sirepo_user'

#: See sirepo.sr_unit
SR_UNIT_TEST_IN_REQUEST = 'test_in_request'

#: WSGIApp instance (see `init_by_server`)
_wsgi_app = None

#: Default file to serve on errors
DEFAULT_ERROR_FILE = 'server-error.html'

#: Flask app instance, must be bound globally
app = flask.Flask(
    __name__,
    static_folder=str(simulation_db.STATIC_FOLDER),
    template_folder=str(simulation_db.STATIC_FOLDER),
)
app.config.update(
    PROPAGATE_EXCEPTIONS=True,
)

def handle_error(error):
    status_code = 500
    if isinstance(error, werkzeug.exceptions.HTTPException):
        status_code = error.code
    try:
        error_file = simulation_db.SCHEMA_COMMON['customErrors'][str(status_code)]
    except:
        error_file = DEFAULT_ERROR_FILE
    f = flask.send_from_directory(static_dir('html'), error_file)

    return f, status_code

def api_copyNonSessionSimulation():
    req = _json_input()
    sim_type = req['simulationType']
    global_path = simulation_db.find_global_simulation(sim_type, req['simulationId'])
    if global_path:
        data = simulation_db.open_json_file(
            sim_type,
            os.path.join(global_path, simulation_db.SIMULATION_DATA_FILE),
        )
        data['models']['simulation']['isExample'] = False
        data['models']['simulation']['outOfSessionSimulationId'] = req['simulationId']
        res = _save_new_and_reply(data)
        target = simulation_db.simulation_dir(sim_type, simulation_db.parse_sid(data))
        template_common.copy_lib_files(
            data,
            py.path.local(os.path.dirname(global_path)).join('lib'),
            target.join('../lib'),
        )
        template = sirepo.template.import_module(data)
        if hasattr(template, 'copy_related_files'):
            template.copy_related_files(data, global_path, str(target))
        return res
    werkzeug.exceptions.abort(404)
app_copy_nonsession_simulation = api_copyNonSessionSimulation


def api_copySimulation():
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
    return _save_new_and_reply(data)
app_copy_simulation = api_copySimulation


def api_deleteFile():
    req = _json_input()
    filename = werkzeug.secure_filename(req['fileName'])
    search_name = _lib_filename(req['simulationType'], filename, req['fileType'])
    err = _simulations_using_file(req['simulationType'], req['fileType'], search_name)
    if len(err):
        return _json_response({
            'error': 'File is in use in other simulations.',
            'fileList': err,
            'fileName': filename,
        })
    p = _lib_filepath(req['simulationType'], filename, req['fileType'])
    pkio.unchecked_remove(p)
    return _json_response({})
app_delete_file = api_deleteFile


def api_deleteSimulation():
    data = _parse_data_input()
    simulation_db.delete_simulation(data['simulationType'], data['simulationId'])
    return _json_response_ok()
app_delete_simulation = api_deleteSimulation


def api_downloadDataFile(simulation_type, simulation_id, model, frame, suffix=None):
    data = {
        'simulationType': sirepo.template.assert_sim_type(simulation_type),
        'simulationId': simulation_id,
        'modelName': model,
    }
    options = pkcollections.Dict(data)
    options.suffix = suffix
    frame = int(frame)
    template = sirepo.template.import_module(data)
    if frame >= 0:
        data['report'] = template.get_animation_name(data)
    else:
        data['report'] = model
    run_dir = simulation_db.simulation_run_dir(data)
    filename, content, content_type = template.get_data_file(run_dir, model, frame, options=options)
    return _as_attachment(flask.make_response(content), content_type, filename)
app_download_data_file = api_downloadDataFile


def api_downloadFile(simulation_type, simulation_id, filename):
    lib = simulation_db.simulation_lib_dir(simulation_type)
    filename = werkzeug.secure_filename(filename)
    p = lib.join(filename)
    if simulation_type == 'srw':
        attachment_name = filename
    else:
        # strip file_type prefix from attachment filename
        attachment_name = re.sub(r'^.*?-.*?\.', '', filename)
    return flask.send_file(str(p), as_attachment=True, attachment_filename=attachment_name)
app_download_file = api_downloadFile


def api_errorLogging():
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
    return _json_response_ok()
app_error_logging = api_errorLogging


def api_exportArchive(simulation_type, simulation_id, filename):
    from sirepo import exporter
    fn, mt = exporter.create_archive(simulation_type, simulation_id, filename)
    return flask.send_file(
        str(fn),
        as_attachment=True,
        attachment_filename=filename,
        mimetype=mt,
        #TODO(pjm): the browser caches HTML files, may need to add explicit times
        # to other calls to send_file()
        cache_timeout=1,
    )


def api_favicon():
    """Routes to favicon.ico file."""
    return flask.send_from_directory(
        str(simulation_db.STATIC_FOLDER.join('img')),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )
app_favicon = api_favicon


def api_listFiles(simulation_type, simulation_id, file_type):
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
app_file_list = api_listFiles


def api_findByName(simulation_type, application_mode, simulation_name):
    if cfg.oauth_login:
        from sirepo import oauth
        oauth.set_default_state(logged_out_as_anonymous=True)
    redirect_uri = None
    # use the existing named simulation, or copy it from the examples
    rows = simulation_db.iterate_simulation_datafiles(simulation_type, simulation_db.process_simulation_list, {
        'simulation.name': simulation_name,
        'simulation.isExample': True,
    })
    if len(rows) == 0:
        for s in simulation_db.examples(simulation_type):
            if s['models']['simulation']['name'] == simulation_name:
                simulation_db.save_new_example(s)
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
app_find_by_name = api_findByName


def api_getApplicationData(filename=''):
    """Get some data from the template

    Args:
        filename (str): if supplied, result is file attachment

    Returns:
        response: may be a file or JSON
    """
    data = _parse_data_input()
    res = sirepo.template.import_module(data).get_application_data(data)
    if filename:
        assert isinstance(res, _PY_PATH_LOCAL_CLASS), \
            '{}: template did not return a file'.format(res)
        return flask.send_file(
            str(res),
            mimetype='application/octet-stream',
            as_attachment=True,
            attachment_filename=filename,
        )
    return _json_response(res)
app_get_application_data = api_getApplicationData


def api_importArchive():
    """
    Args:
        simulation_type (str): which simulation type
    Params:
        data: what to import
    """
    import sirepo.importer

    data = sirepo.importer.do_form(flask.request.form)
    return javascript_redirect(
        '/{}#/source/{}'.format(
            data.simulationType,
            data.models.simulation.simulationId,
        ),
    )


def api_importFile(simulation_type=None):
    """
    Args:
        simulation_type (str): which simulation type
    Params:
        file: file data
        folder: where to import to
    """
    import sirepo.importer

    error = None
    f = None
    try:
        template = simulation_type and sirepo.template.import_module(simulation_type)
        f = flask.request.files.get('file')
        assert f, \
            ValueError('must supply a file')
        if pkio.has_file_extension(f.filename, 'json'):
            data = sirepo.importer.read_json(f.read(), template)
        #TODO(pjm): need a separate URI interface to importer, added exception for rs4pi for now
        # (dicom input is normally a zip file)
        elif pkio.has_file_extension(f.filename, 'zip') and simulation_type != 'rs4pi':
            data = sirepo.importer.read_zip(f.stream, template)
        else:
            assert simulation_type, \
                'simulation_type is required param for non-zip|json imports'
            assert hasattr(template, 'import_file'), \
                ValueError('Only zip files are supported')
            data = template.import_file(
                flask.request,
                simulation_db.simulation_lib_dir(simulation_type),
                simulation_db.tmp_dir(),
            )
        #TODO(robnagler) need to validate folder
        data.models.simulation.folder = flask.request.form['folder']
        return _save_new_and_reply(data)
    except Exception as e:
        pkdlog('{}: exception: {}', f and f.filename, pkdexc())
        error = str(e.message) if hasattr(e, 'message') else str(e)
    return _json_response({'error': error})

app_import_file = api_importFile



def api_homePage():
    return _render_root_page('sr-landing-page', pkcollections.Dict())
light_landing_page = api_homePage


def api_newSimulation():
    new_simulation_data = _parse_data_input()
    sim_type = new_simulation_data['simulationType']
    data = simulation_db.default_data(sim_type)
    data['models']['simulation']['name'] = new_simulation_data['name']
    data['models']['simulation']['folder'] = new_simulation_data['folder']
    template = sirepo.template.import_module(sim_type)
    if hasattr(template, 'new_simulation'):
        template.new_simulation(data, new_simulation_data)
    return _save_new_and_reply(data)
app_new_simulation = api_newSimulation


def api_oauthAuthorized(oauth_type):
    if cfg.oauth_login:
        from sirepo import oauth
        return oauth.authorized_callback(app, oauth_type)
    raise RuntimeError('OAUTH Login not configured')
app_oauth_authorized = api_oauthAuthorized


def api_oauthLogin(simulation_type, oauth_type):
    if cfg.oauth_login:
        from sirepo import oauth
        return oauth.authorize(simulation_type, app, oauth_type)
    raise RuntimeError('OAUTH Login not configured')
app_oauth_login = api_oauthLogin


def api_oauthLogout(simulation_type):
    if cfg.oauth_login:
        from sirepo import oauth
        return oauth.logout(simulation_type)
    raise RuntimeError('OAUTH Login not configured')
app_oauth_logout = api_oauthLogout


def api_pythonSource(simulation_type, simulation_id, model=None, report=None):
    import string
    data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
    template = sirepo.template.import_module(data)
    sim_name = data.models.simulation.name.lower()
    report_rider = '' if report is None else '-' + report.lower()
    py_name = sim_name + report_rider
    py_name = re.sub(r'[\"&\'()+,/:<>?\[\]\\`{}|]', '', py_name)
    py_name = re.sub(r'\s', '-', py_name)
    return _as_attachment(
        flask.make_response(template.python_source_for_model(data, model)),
        'text/x-python',
        '{}.py'.format(py_name),
    )
app_python_source = api_pythonSource


def api_robotsTxt():
    """Tell robots to go away"""
    return flask.Response(
        'User-agent: *\nDisallow: /\n',
        mimetype='text/plain',
    )
app_robots_txt = api_robotsTxt


def api_root(simulation_type):
    try:
        sirepo.template.assert_sim_type(simulation_type)
    except AssertionError:
        if simulation_type == 'warp':
            return flask.redirect('/warppba', code=301)
        if simulation_type == 'fete':
            return flask.redirect('/warpvnd', code=301)
        pkdlog('{}: uri not found', simulation_type)
        werkzeug.exceptions.abort(404)
    if cfg.oauth_login:
        from sirepo import oauth
        values = oauth.set_default_state()
    else:
        values = pkcollections.Dict()
    values.app_name = simulation_type
    values.oauth_login = cfg.oauth_login
    return _render_root_page('index', values)
app_root = api_root


def api_runCancel():
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
app_run_cancel = api_runCancel


def api_runSimulation():
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
app_run_simulation = api_runSimulation


def api_runStatus():
    data = _parse_data_input()
    return _json_response(_simulation_run_status(data))
app_run_status = api_runStatus


def api_saveSimulationData():
    data = _parse_data_input(validate=True)
    res = _validate_serial(data)
    if res:
        return res
    simulation_type = data['simulationType']
    template = sirepo.template.import_module(simulation_type)
    if hasattr(template, 'prepare_for_save'):
        data = template.prepare_for_save(data)
    data = simulation_db.save_simulation_json(data)
    return app_simulation_data(
        data['simulationType'],
        data['models']['simulation']['simulationId'],
        pretty=False,
    )
app_save_simulation_data = api_saveSimulationData


def api_simulationData(simulation_type, simulation_id, pretty):
    #TODO(robnagler) need real type transforms for inputs
    pretty = bool(int(pretty))
    try:
        data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
        template = sirepo.template.import_module(simulation_type)
        if hasattr(template, 'prepare_for_client'):
            data = template.prepare_for_client(data)
        response = _json_response(
            data,
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
app_simulation_data = api_simulationData


def api_simulationFrame(frame_id):
    #TODO(robnagler) startTime is reportParametersHash; need version on URL and/or param names in URL
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    data = dict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data)
    data['report'] = template.get_animation_name(data)
    run_dir = simulation_db.simulation_run_dir(data)
    model_data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    frame = template.get_simulation_frame(run_dir, data, model_data)
    response = _json_response(frame)
    if 'error' not in frame and template.WANT_BROWSER_FRAME_CACHE:
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(365)
        response.headers['Cache-Control'] = 'public, max-age=31536000'
        response.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    else:
        _no_cache(response)
    return response
app_simulation_frame = api_simulationFrame


def api_listSimulations():
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
app_simulation_list = api_listSimulations


def api_simulationSchema():
    sim_type = sirepo.template.assert_sim_type(flask.request.form['simulationType'])
    return _json_response(simulation_db.get_schema(sim_type))
app_simulation_schema = api_simulationSchema


def api_srLandingPage():
    return flask.redirect('/light')
sr_landing_page = api_srLandingPage


def api_srUnit():
    getattr(app, SR_UNIT_TEST_IN_REQUEST)()
    return ''
app_sr_unit = api_srUnit


def api_updateFolder():
    #TODO(robnagler) Folder should have a serial, or should it be on data
    data = _parse_data_input()
    old_name = data['oldName']
    new_name = data['newName']
    for row in simulation_db.iterate_simulation_datafiles(data['simulationType'], _simulation_data):
        folder = row['models']['simulation']['folder']
        if folder.startswith(old_name):
            row['models']['simulation']['folder'] = re.sub(re.escape(old_name), new_name, folder, 1)
            simulation_db.save_simulation_json(row)
    return _json_response_ok()
app_update_folder = api_updateFolder


def api_uploadFile(simulation_type, simulation_id, file_type):
    f = flask.request.files['file']
    filename = werkzeug.secure_filename(f.filename)
    p = _lib_filepath(simulation_type, filename, file_type)
    err = None
    file_list = None
    if p.check():
        confirm = flask.request.form['confirm'] if 'confirm' in flask.request.form else None
        if not confirm:
            search_name = _lib_filename(simulation_type, filename, file_type)
            file_list = _simulations_using_file(simulation_type, file_type, search_name, ignore_sim_id=simulation_id)
            if file_list:
                err = 'File is in use in other simulations. Please confirm you would like to replace the file for all simulations.'
    if not err:
        pkio.mkdir_parent_only(p)
        f.save(str(p))
        template = sirepo.template.import_module(simulation_type)
        if hasattr(template, 'validate_file'):
            err = template.validate_file(file_type, str(p))
            if err:
                pkio.unchecked_remove(p)
    if err:
        return _json_response({
            'error': err,
            'filename': filename,
            'fileList': file_list,
            'fileType': file_type,
            'simulationId': simulation_id,
        })
    return _json_response({
        'filename': filename,
        'fileType': file_type,
        'simulationId': simulation_id,
    })
app_upload_file = api_uploadFile


def all_uids():
    """List of all users

    Returns:
        set: set of all uids
    """
    if not cfg.oauth_login:
        return set()
    from sirepo import oauth
    return oauth.all_uids(app)


def clear_session_user():
    """Remove the current user from the flask session.
    """
    if _SESSION_KEY_USER in flask.session:
        del flask.session[_SESSION_KEY_USER]


def init(db_dir=None, uwsgi=None):
    """Initialize globals and populate simulation dir"""
    from sirepo import uri_router

    if db_dir:
        cfg.db_dir = py.path.local(db_dir)
    else:
        db_dir = cfg.db_dir
    uri_router.init(app, sys.modules[__name__], simulation_db)
    global _wsgi_app
    _wsgi_app = _WSGIApp(app, uwsgi)
    _BeakerSession().sirepo_init_app(app, db_dir)
    simulation_db.init_by_server(app, sys.modules[__name__])

    for err, file in simulation_db.SCHEMA_COMMON['customErrors'].items():
        app.register_error_handler(int(err), handle_error)

    return app


def javascript_redirect(redirect_uri):
    """Redirect using javascript for safari browser which doesn't support hash redirects.
    """
    return flask.render_template(
        'html/javascript-redirect.html',
        redirect_uri=redirect_uri
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
def _cfg_db_dir(value):
    """Config value or root package's parent or cwd with _DEFAULT_SUBDIR"""
    from pykern import pkinspect

    if value:
        assert os.path.isabs(value), \
            '{}: SIREPO_SERVER_DB_DIR must be absolute'.format(value)
        assert os.path.isdir(value), \
            '{}: SIREPO_SERVER_DB_DIR must be a directory and exist'.format(value)
        value = py.path.local(value)
    else:
        assert pkconfig.channel_in('dev'), \
            'SIREPO_SERVER_DB_DIR must be configured except in DEV'
        fn = sys.modules[pkinspect.root_package(_cfg_db_dir)].__file__
        root = py.path.local(py.path.local(py.path.local(fn).dirname).dirname)
        # Check to see if we are in our dev directory. This is a hack,
        # but should be reliable.
        if not root.join('requirements.txt').check():
            # Don't run from an install directory
            root = py.path.local('.')
        value = pkio.mkdir_parent(root.join(_DEFAULT_DB_SUBDIR))
    return value


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


def _json_input(assert_sim_type=True):
    req = flask.request
    if req.mimetype != 'application/json':
        pkdlog('{}: req.mimetype is not application/json', req.mimetype)
        raise werkzeug.exceptions.BadRequest('expecting application/json')
    # Adapted from flask.wrappers.Request.get_json
    # We accept a request charset against the specification as
    # certain clients have been using this in the past.  This
    # fits our general approach of being nice in what we accept
    # and strict in what we send out.
    charset = req.mimetype_params.get('charset')
    data = req.get_data(cache=False)
    res = simulation_db.json_load(data, encoding=charset)
    if assert_sim_type and 'simulationType' in res:
        res.simulationType = sirepo.template.assert_sim_type(res.simulationType)
    return res


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


def _lib_filename(simulation_type, filename, file_type):
    if simulation_type == 'srw':
        return filename
    return werkzeug.secure_filename('{}.{}'.format(file_type, filename))


def _lib_filepath(simulation_type, filename, file_type):
    lib = simulation_db.simulation_lib_dir(simulation_type)
    return lib.join(_lib_filename(simulation_type, filename, file_type))


def _no_cache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'


def _parse_data_input(validate=False):
    data = _json_input(assert_sim_type=False)
    return simulation_db.fixup_old_data(data)[0] if validate else data


def _render_root_page(page, values):
    values.source_cache_key = _source_cache_key()
    values.app_version = simulation_db.app_version()
    return flask.render_template(
        'html/{}.html'.format(page),
        **values
    )


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
        template = sirepo.template.import_module(data)
        if is_processing:
            if not rep.cached_data:
                return _simulation_error(
                    'input file not found, but job is running',
                    rep.input_file,
                )
        else:
            is_running = False
            if rep.run_dir.exists():
                if hasattr(template, 'prepare_output_file') and 'models' in data:
                    template.prepare_output_file(rep, data)
                res2, err = simulation_db.read_result(rep.run_dir)
                if err:
                    if simulation_db.is_parallel(data):
                        # allow parallel jobs to use template to parse errors below
                        res['state'] = 'error'
                    else:
                        return _simulation_error(err, 'error in read_result', rep.run_dir)
                else:
                    res = res2
        if simulation_db.is_parallel(data):
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


def _simulations_using_file(simulation_type, file_type, search_name, ignore_sim_id=None):
    res = []
    template = sirepo.template.import_module(simulation_type)
    if not hasattr(template, 'validate_delete_file'):
        return res
    for row in simulation_db.iterate_simulation_datafiles(simulation_type, _simulation_data):
        if template.validate_delete_file(row, search_name, file_type):
            sim = row['models']['simulation']
            if ignore_sim_id and sim['simulationId'] == ignore_sim_id:
                continue
            if sim['folder'] == '/':
                res.append('/{}'.format(sim['name']))
            else:
                res.append('{}/{}'.format(sim['folder'], sim['name']))
    return res


def _source_cache_key():
    if cfg.enable_source_cache_key:
        return '?{}'.format(simulation_db.app_version())
    return ''


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

def static_dir(dir_name):
    return str(simulation_db.STATIC_FOLDER.join(dir_name))


cfg = pkconfig.init(
    beaker_session=dict(
        key=('sirepo_' + pkconfig.cfg.channel, str, 'Beaker: Name of the cookie key used to save the session under'),
        secret=(None, _cfg_session_secret, 'Beaker: Used with the HMAC to ensure session integrity'),
        secure=(False, bool, 'Beaker: Whether or not the session cookie should be marked as secure'),
    ),
    db_dir=(None, _cfg_db_dir, 'where database resides'),
    job_queue=('Background', runner.cfg_job_queue, 'how to run long tasks: Celery or Background'),
    foreground_time_limit=(5 * 60, _cfg_time_limit, 'timeout for short (foreground) tasks'),
    oauth_login=(False, bool, 'OAUTH: enable login'),
    enable_source_cache_key=(True, bool, 'enable source cache key, disable to allow local file edits in Chrome'),
)
