# -*- coding: utf-8 -*-
u"""Flask server interface

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import feature_config
from sirepo import http_reply
from sirepo import http_request
from sirepo import simulation_db
from sirepo import srschema
from sirepo import uri_router
import flask
import importlib
import re
import sirepo.sim_data
import sirepo.srdb
import sirepo.template
import sirepo.uri
import sirepo.util
import urllib
import werkzeug
import werkzeug.exceptions


#TODO(pjm): this import is required to work-around template loading in listSimulations, see #1151
if any(k in feature_config.cfg().sim_types for k in ('flash', 'rs4pi', 'radia', 'synergia', 'warppba', 'warpvnd')):
    import h5py

#: If google_tag_manager_id set, string to insert in landing pages for google analytics
_google_tag_manager = None

#: what to match in landing pages to insert `_google_tag_manager`
_google_tag_manager_re = re.compile('(?=</head>)', flags=re.IGNORECASE)

#: See sirepo.srunit
SRUNIT_TEST_IN_REQUEST = 'srunit_test_in_request'

#: Default file to serve on errors
DEFAULT_ERROR_FILE = 'server-error.html'

_ROBOTS_TXT = None

#: Global app value (only here so instance not lost)
_app = None

@api_perm.require_user
def api_copyNonSessionSimulation():
    req = http_request.parse_post(id=True, template=True)
    simulation_db.verify_app_directory(req.type)
    src = pkio.py_path(
        simulation_db.find_global_simulation(
            req.type,
            req.id,
            checked=True,
        ),
    )
    data = simulation_db.open_json_file(
        req.type,
        src.join(simulation_db.SIMULATION_DATA_FILE),
    )
    data.pkdel('report')
    data.models.simulation.isExample = False
    data.models.simulation.outOfSessionSimulationId = req.id
    res = _save_new_and_reply(data)
    sirepo.sim_data.get_class(req.type).lib_files_from_other_user(
        data,
        simulation_db.lib_dir_from_sim_dir(src),
    )
    target = simulation_db.simulation_dir(req.type, data.models.simulation.simulationId)
    #TODO(robnagler) does not work, supervisor needs to be notified to
    # copy the simulation state.
    # if hasattr(req.template, 'copy_related_files'):
    #     req.template.copy_related_files(data, str(src), str(target))
    return res


@api_perm.require_user
def api_copySimulation():
    """Takes the specified simulation and returns a newly named copy with the suffix ( X)"""
    req = http_request.parse_post(id=True, folder=True, name=True)
    d = simulation_db.read_simulation_json(req.type, sid=req.id)
    d.models.simulation.pkupdate(
        name=req.name,
        folder=req.folder,
        isExample=False,
        outOfSessionSimulationId='',
    )
    return _save_new_and_reply(d)


@api_perm.require_user
def api_deleteFile():
    req = http_request.parse_post(filename=True, file_type=True)
    e = _simulations_using_file(req)
    if len(e):
        return http_reply.gen_json({
            'error': 'File is in use in other simulations.',
            'fileList': e,
            'fileName': req.filename,
        })

    # Will not remove resource (standard) lib files
    pkio.unchecked_remove(_lib_file_write_path(req))
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_deleteSimulation():
    req = http_request.parse_post(id=True)
    simulation_db.delete_simulation(req.type, req.id)
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_downloadFile(simulation_type, simulation_id, filename):
    #TODO(pjm): simulation_id is an unused argument
    req = http_request.parse_params(type=simulation_type, filename=filename)
    n = req.sim_data.lib_file_name_without_type(req.filename)
    p = req.sim_data.lib_file_abspath(req.filename)
    try:
        return http_reply.gen_file_as_attachment(p, filename=n)
    except Exception as e:
        if pkio.exception_is_not_found(e):
            sirepo.util.raise_not_found('lib_file={} not found', p)
        raise


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
    req = http_request.parse_params(
        filename=filename,
        id=simulation_id,
        type=simulation_type,
    )
    from sirepo import exporter
    return exporter.create_archive(req)


@api_perm.allow_visitor
def api_favicon():
    """Routes to favicon.ico file."""
    return flask.send_from_directory(
        static_dir('img'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon',
    )


@api_perm.require_user
def api_listFiles(simulation_type, simulation_id, file_type):
    #TODO(pjm): simulation_id is an unused argument
    req = http_request.parse_params(type=simulation_type, file_type=file_type)
    return http_reply.gen_json(
        req.sim_data.lib_file_names_for_type(req.file_type),
    )


@api_perm.allow_visitor
def api_findByName(simulation_type, application_mode, simulation_name):
    req = http_request.parse_params(type=simulation_type)
    return http_reply.gen_redirect_for_local_route(
        req.type,
        'findByName',
        PKDict(
            applicationMode=application_mode,
            simulationName=simulation_name,
        ),
    )


@api_perm.require_user
def api_findByNameWithAuth(simulation_type, application_mode, simulation_name):
    req = http_request.parse_params(type=simulation_type)
    #TODO(pjm): need to unquote when redirecting from saved cookie redirect?
    if hasattr(urllib, 'unquote'):
        # python2
        simulation_name = urllib.unquote(simulation_name)
    else:
        # python3
        simulation_name = urllib.parse.unquote(simulation_name)
    # use the existing named simulation, or copy it from the examples
    rows = simulation_db.iterate_simulation_datafiles(
        req.type,
        simulation_db.process_simulation_list,
        {
            'simulation.name': simulation_name,
            'simulation.isExample': True,
        },
    )
    if len(rows) == 0:
        for s in simulation_db.examples(req.type):
            if s['models']['simulation']['name'] != simulation_name:
                continue
            simulation_db.save_new_example(s)
            rows = simulation_db.iterate_simulation_datafiles(
                req.type,
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
                req.type,
            )
    m = simulation_db.get_schema(req.type).appModes[application_mode]
    return http_reply.gen_redirect_for_local_route(
        req.type,
        m.localRoute,
        PKDict(simulationId=rows[0].simulationId),
        query=m.includeMode and PKDict(application_mode=application_mode),
    )


@api_perm.require_user
def api_getApplicationData(filename=None):
    """Get some data from the template

    Args:
        filename (str): if supplied, result is file attachment

    Returns:
        response: may be a file or JSON
    """
    req = http_request.parse_post(template=True, filename=filename or None)
    with simulation_db.tmp_dir() as d:
        assert 'method' in req.req_data
        res = req.template.get_application_data(req.req_data, tmp_dir=d)
        assert res != None, f'unhandled application data method: {req.req_data.method}'
        if 'filename' in req and isinstance(res, pkconst.PY_PATH_LOCAL_TYPE):
            return http_reply.gen_file_as_attachment(
                res,
                filename=req.filename,
                content_type=req.req_data.get('contentType', None)
            )
        return http_reply.gen_json(res)


@api_perm.allow_cookieless_require_user
def api_importArchive():
    """
    Params:
        data: what to import
    """
    import sirepo.importer
    # special http_request parsing here
    data = sirepo.importer.do_form(flask.request.form)
    m = simulation_db.get_schema(data.simulationType).appModes.default
    return http_reply.gen_redirect_for_local_route(
        data.simulationType,
        m.localRoute,
        PKDict(simulationId=data.models.simulation.simulationId),
    )


@api_perm.require_user
def api_importFile(simulation_type):
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
        f = flask.request.files.get('file')
        if not f:
            raise sirepo.util.Error('must supply a file')
        req = http_request.parse_params(
            filename=f.filename,
            folder=flask.request.form.get('folder'),
            id=flask.request.form.get('simulationId'),
            template=True,
            type=simulation_type,
        )
        req.file_stream = f.stream
        req.import_file_arguments = flask.request.form.get('arguments', '')

        def s(data):
            data.models.simulation.folder = req.folder
            data.models.simulation.isExample = False
            return _save_new_and_reply(data)

        if pkio.has_file_extension(req.filename, 'json'):
            data = sirepo.importer.read_json(req.file_stream.read(), req.type)
        #TODO(pjm): need a separate URI interface to importer, added exception for rs4pi for now
        # (dicom input is normally a zip file)
        elif pkio.has_file_extension(req.filename, 'zip') and req.type != 'rs4pi':
            data = sirepo.importer.read_zip(req.file_stream.read(), sim_type=req.type)
        else:
            if not hasattr(req.template, 'import_file'):
                raise sirepo.util.Error('Only zip files are supported')
            with simulation_db.tmp_dir() as d:
                data = req.template.import_file(req, tmp_dir=d, reply_op=s)
            if 'error' in data:
                return http_reply.gen_json(data)
        return s(data)
    except werkzeug.exceptions.HTTPException:
        raise
    except sirepo.util.Reply:
        raise
    except Exception as e:
        pkdlog('{}: exception: {}', f and f.filename, pkdexc())
        #TODO(robnagler) security issue here. Really don't want to report errors to user
        if hasattr(e, 'args'):
            if len(e.args) == 1:
                error = str(e.args[0])
            else:
                error = str(e.args)
        else:
            error = str(e)
    return http_reply.gen_json({
        'error': error if error else 'An unknown error occurred',
    })


@api_perm.allow_visitor
def api_homePage(path_info=None):
    return api_staticFile('en/' + (path_info or 'landing.html'))


@api_perm.require_user
def api_exportJupyterNotebook(simulation_type, simulation_id, model=None, title=None):
    req = http_request.parse_params(type=simulation_type, id=simulation_id, template=True)
    m = model and req.sim_data.parse_model(model)
    d = simulation_db.read_simulation_json(req.type, sid=req.id)
    return http_reply.gen_file_as_attachment(
        req.template.jupyter_notebook_for_model(d, m),
        '{}.{}'.format(
            d.models.simulation.name + ('-' + title if title else ''),
            'ipynb',
        ),
        content_type='application/json'
    )


@api_perm.require_user
def api_newSimulation():
    req = http_request.parse_post(template=True, folder=True, name=True)
    d = simulation_db.default_data(req.type)
#TODO(pjm): update fields from schema values across new_simulation_data values
    d.models.simulation.pkupdate(
        name=req.name,
        folder=req.folder,
        notes=req.req_data.get('notes', ''),
    )
    if hasattr(req.template, 'new_simulation'):
        req.template.new_simulation(d, req.req_data)
    return _save_new_and_reply(d)


@api_perm.require_user
def api_pythonSource(simulation_type, simulation_id, model=None, title=None):
    req = http_request.parse_params(type=simulation_type, id=simulation_id, template=True)
    m = model and req.sim_data.parse_model(model)
    d = simulation_db.read_simulation_json(req.type, sid=req.id)
    return http_reply.gen_file_as_attachment(
        req.template.python_source_for_model(d, m),
        '{}.{}'.format(
            d.models.simulation.name + ('-' + title if title else ''),
            'madx' if m == 'madx' else 'py',
        ),
    )


@api_perm.allow_visitor
def api_robotsTxt():
    """Disallow the app (dev, prod) or / (alpha, beta)"""
    global _ROBOTS_TXT
    if not _ROBOTS_TXT:
        # We include dev so we can test
        if pkconfig.channel_in('prod', 'dev'):
            u = [
                sirepo.uri.api('root', params={'path_info': x})
                for x in sorted(feature_config.cfg().sim_types)
            ]
        else:
            u = ['/']
        _ROBOTS_TXT = ''.join(
            ['User-agent: *\n'] + ['Disallow: /{}\n'.format(x) for x in u],
        )
    return flask.Response(_ROBOTS_TXT, mimetype='text/plain')


@api_perm.allow_visitor
def api_root(path_info):
    if sirepo.template.is_sim_type(path_info):
        return _render_root_page('index', PKDict(app_name=path_info))
    u = sirepo.uri.unchecked_root_redirect(path_info)
    if u:
        return http_reply.gen_redirect(u)
    sirepo.util.raise_not_found(f'uknown path={path_info}')


@api_perm.require_user
def api_saveSimulationData():
    # do not fixup_old_data yet
    req = http_request.parse_post(id=True, template=True)
    d = req.req_data
    simulation_db.validate_serial(d)
    d = simulation_db.fixup_old_data(d)[0]
    if hasattr(req.template, 'prepare_for_save'):
        d = req.template.prepare_for_save(d)
    d = simulation_db.save_simulation_json(d)
    return api_simulationData(
        d.simulationType,
        d.models.simulation.simulationId,
    )


@api_perm.require_user
def api_simulationData(simulation_type, simulation_id, pretty=False, section=None):
    """First entry point for a simulation

    Might be non-session simulation copy (see `simulation_db.CopyRedirect`).
    We have to allow a non-user to get data.
    """
    #TODO(pjm): pretty is an unused argument
    #TODO(robnagler) need real type transforms for inputs
    req = http_request.parse_params(type=simulation_type, id=simulation_id, template=True)
    try:
        d = simulation_db.read_simulation_json(req.type, sid=req.id)
        if hasattr(req.template, 'prepare_for_client'):
            d = req.template.prepare_for_client(d)
        resp = http_reply.gen_json(d)
    except simulation_db.CopyRedirect as e:
        if e.sr_response['redirect'] and section:
            e.sr_response['redirect']['section'] = section
        resp = http_reply.gen_json(e.sr_response)
    return http_reply.headers_for_no_cache(resp)


@api_perm.require_user
def api_listSimulations():
    req = http_request.parse_post()
    simulation_db.verify_app_directory(req.type)
    return http_reply.gen_json(
        sorted(
            simulation_db.iterate_simulation_datafiles(
                req.type,
                simulation_db.process_simulation_list,
                req.req_data.get('search'),
            ),
            key=lambda row: row['name'],
        )
    )


# visitor rather than user because error pages are rendered by the application
@api_perm.allow_visitor
def api_simulationSchema():
    return http_reply.gen_json(
        simulation_db.get_schema(
            http_request.parse_params(
                type=flask.request.form['simulationType'],
            ).type,
        ),
    )


@api_perm.allow_visitor
def api_srwLight():
    return _render_root_page('light', PKDict())


@api_perm.allow_visitor
def api_srUnit():
    v = getattr(flask.current_app, SRUNIT_TEST_IN_REQUEST)
    if v.want_user:
        import sirepo.auth
        sirepo.auth.set_user_for_utils()
    if v.want_cookie:
        import sirepo.cookie
        sirepo.cookie.set_sentinel()
    v.op()
    return http_reply.gen_json_ok()


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
    if not path_info:
        raise util.raise_not_found('empty path info')
    p = pkio.py_path(flask.safe_join(str(simulation_db.STATIC_FOLDER), path_info))
    r = None
    if _google_tag_manager and re.match(r'^en/[^/]+html$', path_info):
        return http_reply.headers_for_cache(
            flask.make_response(
                _google_tag_manager_re.sub(
                    _google_tag_manager,
                    pkio.read_text(p),
                ),
            ),
            path=p,
        )
    if re.match(r'^html/[^/]+html$', path_info):
        return http_reply.render_html(p)
    return flask.send_file(p, conditional=True)


@api_perm.require_user
def api_updateFolder():
    #TODO(robnagler) Folder should have a serial, or should it be on data
    req = http_request.parse_post()
    o = srschema.parse_folder(req.req_data['oldName'])
    if o == '/':
        raise util.Error('cannot rename root ("/") folder')
    n = srschema.parse_folder(req.req_data['newName'])
    if n == '/':
        raise util.Error('cannot folder to root ("/")')
    for r in simulation_db.iterate_simulation_datafiles(req.type, _simulation_data_iterator):
        f = r.models.simulation.folder
        l = o.lower()
        if f.lower() == o.lower():
            r.models.simulation.folder = n
        elif f.lower().startswith(o.lower() + '/'):
            r.models.simulation.folder = n + f[len():]
        else:
            continue
        simulation_db.save_simulation_json(r)
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_uploadFile(simulation_type, simulation_id, file_type):
    f = flask.request.files['file']
    req = http_request.parse_params(
        file_type=file_type,
        filename=f.filename,
        id=simulation_id,
        template=True,
        type=simulation_type,
    )
    e = None
    in_use = None
    with simulation_db.tmp_dir() as d:
        t = d.join(req.filename)
        f.save(str(t))
        if hasattr(req.template, 'validate_file'):
            # Note: validate_file may modify the file
            e = req.template.validate_file(req.file_type, t)
        if (
            not e and req.sim_data.lib_file_exists(req.filename)
            and not flask.request.form.get('confirm')
        ):
            in_use = _simulations_using_file(req, ignore_sim_id=req.id)
            if in_use:
                e = 'File is in use in other simulations. Please confirm you would like to replace the file for all simulations.'
        if e:
            return http_reply.gen_json({
                'error': e,
                'filename': req.filename,
                'fileList': in_use,
                'fileType': req.file_type,
                'simulationId': req.id,
            })
        t.rename(_lib_file_write_path(req))
    return http_reply.gen_json({
        'filename': req.filename,
        'fileType': req.file_type,
        'simulationId': req.id,
    })


def init(uwsgi=None, use_reloader=False):
    """Initialize globals and populate simulation dir"""
    global _app

    if _app:
        return
    global _google_tag_manager
    if cfg.google_tag_manager_id:
        _google_tag_manager = f'''<script>
    (function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','{cfg.google_tag_manager_id}');
    </script>'''
    #: Flask app instance, must be bound globally
    _app = flask.Flask(
        __name__,
        static_folder=None,
        template_folder=str(simulation_db.STATIC_FOLDER),
    )
    _app.config.update(
        PROPAGATE_EXCEPTIONS=True,
    )
    _app.sirepo_uwsgi = uwsgi
    _app.sirepo_use_reloader = use_reloader
    uri_router.init(_app, simulation_db)
    return _app


def init_apis(*args, **kwargs):
    import sirepo.job

    for e, _ in simulation_db.SCHEMA_COMMON['customErrors'].items():
        _app.register_error_handler(int(e), _handle_error)
    sirepo.job.init_by_server(_app)


def _handle_error(error):
    status_code = 500
    if isinstance(error, werkzeug.exceptions.HTTPException):
        status_code = error.code
    try:
        error_file = simulation_db.SCHEMA_COMMON['customErrors'][str(status_code)]['url']
    except Exception:
        error_file = DEFAULT_ERROR_FILE
    return (
        flask.send_from_directory(static_dir('html'), error_file),
        status_code,
    )


def _lib_file_write_path(req):
    return req.sim_data.lib_file_write_path(
        req.sim_data.lib_file_name_with_type(req.filename, req.file_type),
    )


def _render_root_page(page, values):
    values.update(PKDict(
        app_version=simulation_db.app_version(),
        source_cache_key=_source_cache_key(),
        static_files=simulation_db.static_libs(),
    ))
    return http_reply.render_static_jinja(page, 'html', values, cache_ok=True)


def _save_new_and_reply(*args):
    data = simulation_db.save_new_simulation(*args)
    return api_simulationData(
        data['simulationType'],
        data['models']['simulation']['simulationId'],
    )


def _simulation_data_iterator(res, path, data):
    """Iterator function to return entire simulation data
    """
    res.append(data)


def _simulations_using_file(req, ignore_sim_id=None):
    res = []
    for r in simulation_db.iterate_simulation_datafiles(req.type, _simulation_data_iterator):
        if not req.sim_data.lib_file_in_use(r, req.filename):
            continue
        s = r.models.simulation
        if s.simulationId == ignore_sim_id:
            continue
        res.append(
            '{}{}{}'.format(
                s.folder,
                '' if s.folder == '/' else '/',
                s.name,
            )
        )
    return res


def _source_cache_key():
    if cfg.enable_source_cache_key:
        return '?{}'.format(simulation_db.app_version())
    return ''


def static_dir(dir_name):
    return str(simulation_db.STATIC_FOLDER.join(dir_name))


cfg = pkconfig.init(
    enable_source_cache_key=(True, bool, 'enable source cache key, disable to allow local file edits in Chrome'),
    db_dir=pkconfig.ReplacedBy('sirepo.srdb.root'),
    google_tag_manager_id=(None, str, 'enable google analytics with this id'),
)
