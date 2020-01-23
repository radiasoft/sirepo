# -*- coding: utf-8 -*-
u"""Flask server interface

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import feature_config
from sirepo import http_reply
from sirepo import http_request
from sirepo import simulation_db
from sirepo import srdb
from sirepo import uri_router
from sirepo.template import adm
from sirepo.template import template_common
import datetime
import flask
import importlib
import py.path
import re
import sirepo.sim_data
import sirepo.template
import sirepo.uri
import sirepo.util
import time
import urllib
import uuid
import werkzeug
import werkzeug.exceptions


#TODO(pjm): this import is required to work-around template loading in listSimulations, see #1151
if any(k in feature_config.cfg.sim_types for k in ('flash', 'rs4pi', 'synergia', 'warppba', 'warpvnd')):
    import h5py

#: class that py.path.local() returns
_PY_PATH_LOCAL_CLASS = type(pkio.py_path())

#: See sirepo.srunit
SRUNIT_TEST_IN_REQUEST = 'srunit_test_in_request'

#: Default file to serve on errors
DEFAULT_ERROR_FILE = 'server-error.html'

_ROBOTS_TXT = None

#: Global app value (only here so instance not lost)
_app = None

@api_perm.require_user
def api_copyNonSessionSimulation():
    req = http_request.parse_json()
    sim_type = req['simulationType']
    src = py.path.local(simulation_db.find_global_simulation(
        sim_type,
        req['simulationId'],
        checked=True,
    ))
    data = simulation_db.open_json_file(
        sim_type,
        src.join(simulation_db.SIMULATION_DATA_FILE),
    )
    if 'report' in data:
        del data['report']
    data.models.simulation.isExample = False
    data.models.simulation.outOfSessionSimulationId = req.simulationId
    res = _save_new_and_reply(data)
    target = simulation_db.simulation_dir(sim_type, data.models.simulation.simulationId)
    sirepo.sim_data.get_class(sim_type).lib_files_copy(
        data,
        simulation_db.lib_dir_from_sim_dir(src),
        simulation_db.lib_dir_from_sim_dir(target),
    )
    template = sirepo.template.import_module(data)
    if hasattr(template, 'copy_related_files'):
        template.copy_related_files(data, str(src), str(target))
    return res


@api_perm.require_user
def api_copySimulation():
    """Takes the specified simulation and returns a newly named copy with the suffix ( X)"""
    req = http_request.parse_json()
    sim_type = req.simulationType
    name = req.name
    assert name, \
        sirepo.util.err(req, 'No name in request')
    folder = req.folder if 'folder' in req else '/'
    data = simulation_db.read_simulation_json(sim_type, sid=req.simulationId)
    data.models.simulation.name = name
    data.models.simulation.folder = folder
    data.models.simulation.isExample = False
    data.models.simulation.outOfSessionSimulationId = ''
    return _save_new_and_reply(data)


@api_perm.require_user
def api_deleteFile():
    req = http_request.parse_json()
    filename = werkzeug.secure_filename(req['fileName'])
    search_name = _lib_filename(req['simulationType'], filename, req['fileType'])
    err = _simulations_using_file(req['simulationType'], req['fileType'], search_name)
    if len(err):
        return http_reply.gen_json({
            'error': 'File is in use in other simulations.',
            'fileList': err,
            'fileName': filename,
        })
    p = _lib_filepath(req['simulationType'], filename, req['fileType'])
    pkio.unchecked_remove(p)
    return http_reply.gen_json({})


@api_perm.require_user
def api_deleteSimulation():
    data = http_request.parse_data_input()
    simulation_db.delete_simulation(data['simulationType'], data['simulationId'])
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_downloadDataFile(simulation_type, simulation_id, model, frame, suffix=None):
    data = PKDict(
        simulationType=sirepo.template.assert_sim_type(simulation_type),
        simulationId=simulation_id,
        modelName=model,
    )
    f = int(frame)
    t = sirepo.template.import_module(data)
    data.report = sirepo.sim_data.get_class(simulation_type).animation_name(data) \
        if f >= 0 else model
    f, c, t = t.get_data_file(
        simulation_db.simulation_run_dir(data),
        model,
        f,
        options=data.copy().update(suffix=suffix),
    )
    return _as_attachment(flask.make_response(c), t, f)


@api_perm.require_user
def api_downloadFile(simulation_type, simulation_id, filename):
    #TODO(pjm): simulation_id is an unused argument
    n = werkzeug.secure_filename(filename)
    p = simulation_db.simulation_lib_dir(simulation_type).join(n)
    if simulation_type != 'srw':
        # strip file_type prefix from attachment filename
        n = re.sub(r'^.*?-.*?\.', '', n)
    return flask.send_file(str(p), as_attachment=True, attachment_filename=n)


@api_perm.allow_visitor
def api_errorLogging():
    ip = flask.request.remote_addr
    try:
        pkdlog(
            '{}: javascript error: {}',
            ip,
            simulation_db.generate_json(http_request.parse_json(), pretty=True),
        )
    except ValueError as e:
        pkdlog(
            '{}: error parsing javascript app_error: {} input={}',
            ip,
            e,
            flask.request.data.decode('unicode-escape'),
        )
    return http_reply.gen_json_ok()


@api_perm.require_user
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


@api_perm.allow_visitor
def api_favicon():
    """Routes to favicon.ico file."""
    return flask.send_from_directory(
        str(simulation_db.STATIC_FOLDER.join('img')),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@api_perm.require_user
def api_listFiles(simulation_type, simulation_id, file_type):
    #TODO(pjm): simulation_id is an unused argument
    return http_reply.gen_json(
        sorted(
            sirepo.sim_data.get_class(simulation_type).lib_files_for_type(
                werkzeug.secure_filename(file_type),
            ),
        ),
    )

@api_perm.allow_visitor
def api_findByName(simulation_type, application_mode, simulation_name):
    return http_reply.gen_redirect_for_local_route(
        simulation_type,
        'findByName',
        PKDict(
            applicationMode=application_mode,
            simulationName=simulation_name,
        ),
    )


@api_perm.require_user
def api_findByNameWithAuth(simulation_type, application_mode, simulation_name):
    sim_type = sirepo.template.assert_sim_type(simulation_type)
    #TODO(pjm): need to unquote when redirecting from saved cookie redirect?
    simulation_name = urllib.unquote(simulation_name)
    # use the existing named simulation, or copy it from the examples
    rows = simulation_db.iterate_simulation_datafiles(
        sim_type,
        simulation_db.process_simulation_list,
        {
            'simulation.name': simulation_name,
            'simulation.isExample': True,
        },
    )
    if len(rows) == 0:
        for s in simulation_db.examples(sim_type):
            if s['models']['simulation']['name'] != simulation_name:
                continue
            simulation_db.save_new_example(s)
            rows = simulation_db.iterate_simulation_datafiles(
                sim_type,
                simulation_db.process_simulation_list,
                {
                    'simulation.name': simulation_name,
                },
            )
            break
        else:
            sirepo.util.raise_not_found(
                'simulation not found by name={} type={}',
                simulation_name,
                sim_type,
            )
    m = simulation_db.get_schema(sim_type).appModes[application_mode]
    return http_reply.gen_redirect_for_local_route(
        sim_type,
        m.localRoute,
        PKDict(simulationId=rows[0].simulationId),
        query=m.includeMode and PKDict(application_mode=application_mode),
    )


@api_perm.require_user
def api_getApplicationData(filename=''):
    """Get some data from the template

    Args:
        filename (str): if supplied, result is file attachment

    Returns:
        response: may be a file or JSON
    """
    data = http_request.parse_data_input()
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
    return http_reply.gen_json(res)


@api_perm.allow_cookieless_require_user
def api_importArchive():
    """
    Params:
        data: what to import
    """
    import sirepo.importer

    data = sirepo.importer.do_form(flask.request.form)
    return http_reply.gen_redirect_for_local_route(
        data.simulationType,
        route=None,
        params={'simulationId': data.models.simulation.simulationId},
    )


@api_perm.require_user
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
            data = sirepo.importer.read_json(f.read(), simulation_type)
        #TODO(pjm): need a separate URI interface to importer, added exception for rs4pi for now
        # (dicom input is normally a zip file)
        elif pkio.has_file_extension(f.filename, 'zip') and simulation_type != 'rs4pi':
            data = sirepo.importer.read_zip(f.stream, sim_type=simulation_type)
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
            if 'error' in data:
                return http_reply.gen_json(data)
            if 'version' in data:
                # this will force the fixups to run when saved
                del data['version']
        #TODO(robnagler) need to validate folder
        data.models.simulation.folder = flask.request.form['folder']
        data.models.simulation.isExample = False
        return _save_new_and_reply(data)
    except Exception as e:
        pkdlog('{}: exception: {}', f and f.filename, pkdexc())
        error = str(e.message) if hasattr(e, 'message') else str(e)
    return http_reply.gen_json({
        'error': error if error else 'An unknown error occurred',
    })


@api_perm.allow_visitor
def api_homePage(path_info=None):
    return api_staticFile('en/' + (path_info or 'landing.html'))


@api_perm.allow_visitor
def api_homePageOld():
    return _render_root_page('landing-page', PKDict())


@api_perm.require_user
def api_newSimulation():
    new_simulation_data = http_request.parse_data_input()
    sim_type = new_simulation_data['simulationType']
    data = simulation_db.default_data(sim_type)
    #TODO(pjm): update fields from schema values across new_simulation_data values
    data['models']['simulation']['name'] = new_simulation_data['name']
    data['models']['simulation']['folder'] = new_simulation_data['folder']
    if 'notes' in new_simulation_data:
        data['models']['simulation']['notes'] = new_simulation_data['notes']
    template = sirepo.template.import_module(sim_type)
    if hasattr(template, 'new_simulation'):
        template.new_simulation(data, new_simulation_data)
    return _save_new_and_reply(data)


@api_perm.require_user
def api_pythonSource(simulation_type, simulation_id, model=None, report=None):
    d = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
    return _safe_attachment(
        flask.make_response(
            sirepo.template.import_module(d)\
                .python_source_for_model(d, model),
        ),
        d.models.simulation.name + ('-' + report if report else ''),
        'py',
    )

@api_perm.allow_visitor
def api_robotsTxt():
    """Disallow the app (dev, prod) or / (alpha, beta)"""
    global _ROBOTS_TXT
    if not _ROBOTS_TXT:
        # We include dev so we can test
        if pkconfig.channel_in('prod', 'dev'):
            u = [
                sirepo.uri.api('root', params={'simulation_type': x})
                for x in sorted(feature_config.cfg.sim_types)
            ]
        else:
            u = ['/']
        _ROBOTS_TXT = ''.join(
            ['User-agent: *\n'] + ['Disallow: /{}\n'.format(x) for x in u],
        )
    return flask.Response(_ROBOTS_TXT, mimetype='text/plain')


@api_perm.allow_visitor
def api_root(simulation_type):
    try:
        sirepo.template.assert_sim_type(simulation_type)
    except AssertionError:
        if simulation_type == 'warp':
            return http_reply.gen_redirect(sirepo.uri.app_root('warppba'))
        if simulation_type == 'fete':
            return http_reply.gen_redirect(sirepo.uri.app_root('warpvnd'))
        pkdlog('{}: uri not found', simulation_type)
        sirepo.util.raise_not_found('Invalid simulation_type: {}', simulation_type)
    values = PKDict()
    values.app_name = simulation_type
    return _render_root_page('index', values)


@api_perm.require_user
def api_saveSimulationData():
    data = http_request.parse_data_input(validate=True)
    res = _validate_serial(data)
    if res:
        return res
    simulation_type = data['simulationType']
    template = sirepo.template.import_module(simulation_type)
    if hasattr(template, 'prepare_for_save'):
        data = template.prepare_for_save(data)
    data = simulation_db.save_simulation_json(data)
    return api_simulationData(
        data['simulationType'],
        data['models']['simulation']['simulationId'],
        pretty=False,
    )


@api_perm.require_user
def api_simulationData(simulation_type, simulation_id, pretty, section=None):
    """First entry point for a simulation

    Might be non-session simulation copy (see `simulation_db.CopyRedirect`).
    We have to allow a non-user to get data.
    """
    #TODO(robnagler) need real type transforms for inputs
    pretty = bool(int(pretty))
    try:
        _verify_user_dir(simulation_type)
        data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
        template = sirepo.template.import_module(simulation_type)
        if hasattr(template, 'prepare_for_client'):
            data = template.prepare_for_client(data)
        resp = http_reply.gen_json(
            data,
            pretty=pretty,
        )
        if pretty:
            _safe_attachment(
                resp,
                data.models.simulation.name,
                'json',
            )
    except simulation_db.CopyRedirect as e:
        if e.sr_response['redirect'] and section:
            e.sr_response['redirect']['section'] = section
        resp = http_reply.gen_json(e.sr_response)
    return http_reply.headers_for_no_cache(resp)


@api_perm.require_user
def api_listSimulations():
    data = http_request.parse_data_input()
    sim_type = data['simulationType']
    search = data['search'] if 'search' in data else None
    _verify_user_dir(sim_type)
    simulation_db.verify_app_directory(sim_type)
    return http_reply.gen_json(
        sorted(
            simulation_db.iterate_simulation_datafiles(sim_type, simulation_db.process_simulation_list, search),
            key=lambda row: row['name'],
        )
    )

@api_perm.require_user
def api_getServerData():
    input = http_request.parse_data_input(False)
    id = input.id if 'id' in input else None
    d = adm.get_server_data(id)
    if d == None or len(d) == 0:
        raise sirepo.util.UserAlert('Data error', 'no data supplied')
    return http_reply.gen_json(d)


# visitor rather than user because error pages are rendered by the application
@api_perm.allow_visitor
def api_simulationSchema():
    sim_type = sirepo.template.assert_sim_type(flask.request.form['simulationType'])
    return http_reply.gen_json(simulation_db.get_schema(sim_type))


@api_perm.allow_visitor
def api_srwLight():
    return _render_root_page('light', PKDict())


@api_perm.allow_visitor
def api_srUnit():
    v = getattr(flask.current_app, SRUNIT_TEST_IN_REQUEST)
    if v.want_cookie:
        from sirepo import cookie
        cookie.set_sentinel()
    v.op()
    return ''


@api_perm.allow_visitor
def api_staticFile(path_info=None):
    """flask.send_from_directory for static folder.

    Uses safe_join which doesn't allow indexing, paths with '..',
    or absolute paths.

    Args:
        path_info (str): relative path to join
    Returns:
        flask.Response: flask.send_from_directory response
    """
    return flask.send_from_directory(
        str(simulation_db.STATIC_FOLDER),
        path_info,
    )


@api_perm.require_user
def api_updateFolder():
    #TODO(robnagler) Folder should have a serial, or should it be on data
    data = http_request.parse_data_input()
    old_name = data['oldName']
    new_name = data['newName']
    for row in simulation_db.iterate_simulation_datafiles(data['simulationType'], _simulation_data):
        folder = row['models']['simulation']['folder']
        if folder.startswith(old_name):
            row['models']['simulation']['folder'] = re.sub(re.escape(old_name), new_name, folder, 1)
            simulation_db.save_simulation_json(row)
    return http_reply.gen_json_ok()


@api_perm.require_user
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
            err = template.validate_file(file_type, p)
            if err:
                pkio.unchecked_remove(p)
    if err:
        return http_reply.gen_json({
            'error': err,
            'filename': filename,
            'fileList': file_list,
            'fileType': file_type,
            'simulationId': simulation_id,
        })
    return http_reply.gen_json({
        'filename': filename,
        'fileType': file_type,
        'simulationId': simulation_id,
    })


def init(uwsgi=None, use_reloader=False):
    """Initialize globals and populate simulation dir"""
    global _app

    if _app:
        return
    #: Flask app instance, must be bound globally
    _app = flask.Flask(
        __name__,
        static_folder=None,
        template_folder=str(simulation_db.STATIC_FOLDER),
    )
    _app.config.update(
        PROPAGATE_EXCEPTIONS=True,
    )
    _app.sirepo_db_dir = cfg.db_dir
    _app.sirepo_uwsgi = uwsgi
    _app.sirepo_use_reloader = use_reloader
    http_reply.init_by_server(_app)
    simulation_db.init_by_server(_app)
    uri_router.init(_app, simulation_db)
    return _app


def init_apis(app, *args, **kwargs):
    for e, _ in simulation_db.SCHEMA_COMMON['customErrors'].items():
        app.register_error_handler(int(e), _handle_error)
    importlib.import_module(
        'sirepo.' + ('job' if feature_config.cfg.job_supervisor else 'runner')
    ).init_by_server(app)


def _as_attachment(resp, content_type, filename):
    resp.mimetype = content_type
    resp.headers['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return resp


@pkconfig.parse_none
def _cfg_db_dir(value):
    """DEPRECATED"""
    if value is not None:
        srdb.server_init_root(value)
    return srdb.root()


def _cfg_time_limit(value):
    """Sets timeout in seconds"""
    v = int(value)
    assert v > 0
    return v


def _handle_error(error):
    status_code = 500
    if isinstance(error, werkzeug.exceptions.HTTPException):
        status_code = error.code
    try:
        error_file = simulation_db.SCHEMA_COMMON['customErrors'][str(status_code)]['url']
    except Exception:
        error_file = DEFAULT_ERROR_FILE
    f = flask.send_from_directory(static_dir('html'), error_file)

    return f, status_code


def _lib_filename(simulation_type, filename, file_type):
    if simulation_type == 'srw':
        return filename
    return werkzeug.secure_filename('{}.{}'.format(file_type, filename))


def _lib_filepath(simulation_type, filename, file_type):
    lib = simulation_db.simulation_lib_dir(simulation_type)
    return lib.join(_lib_filename(simulation_type, filename, file_type))


def _render_root_page(page, values):
    values.update(PKDict(
        app_version=simulation_db.app_version(),
        source_cache_key=_source_cache_key(),
        static_files=simulation_db.static_libs(),
    ))
    return http_reply.render_static(page, 'html', values, cache_ok=True)


def _safe_attachment(resp, base, suffix):
    return _as_attachment(
        resp,
        http_reply.MIME_TYPE[suffix],
        '{}.{}'.format(
            re.sub(r'[^\w]+', '-', base).strip('-') or 'download',
            suffix,
        ).lower(),
    )


def _save_new_and_reply(*args):
    data = simulation_db.save_new_simulation(*args)
    return api_simulationData(
        data['simulationType'],
        data['models']['simulation']['simulationId'],
        pretty=False,
    )


def _simulation_data(res, path, data):
    """Iterator function to return entire simulation data
    """
    res.append(data)

def _simulations_using_file(simulation_type, file_type, search_name, ignore_sim_id=None):
    res = []
    s = sirepo.sim_data.get_class(simulation_type)
    for row in simulation_db.iterate_simulation_datafiles(simulation_type, _simulation_data):
        if s.is_file_used(row, search_name):
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
    return http_reply.gen_json({
        'state': 'error',
        'error': 'invalidSerial',
        'simulationData': res,
    })


def _verify_user_dir(sim_type):
    # if user dir has been deleted, log out the user #1714
    from sirepo import auth
    uid = auth.logged_in_user()
    if not simulation_db.user_dir_name(uid).check():
        auth.user_dir_not_found(uid)


def static_dir(dir_name):
    return str(simulation_db.STATIC_FOLDER.join(dir_name))


cfg = pkconfig.init(
    db_dir=(None, _cfg_db_dir, 'DEPRECATED: set $SIREPO_SRDB_ROOT'),
    job_queue=(None, str, 'DEPRECATED: set $SIREPO_RUNNER_JOB_CLASS'),
    enable_source_cache_key=(True, bool, 'enable source cache key, disable to allow local file edits in Chrome'),
)
