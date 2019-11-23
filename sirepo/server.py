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
from sirepo import uri_router
from sirepo.template import adm
from sirepo.template import template_common
import datetime
import flask
import importlib
import re
import sirepo.sim_data
import sirepo.srdb
import sirepo.template
import sirepo.uri
import sirepo.util
import time
import urllib
import uuid
import werkzeug
import werkzeug.exceptions


#TODO(pjm): this import is required to work-around template loading in listSimulations, see #1151
if any(k in feature_config.cfg().sim_types for k in ('flash', 'rs4pi', 'synergia', 'warppba', 'warpvnd')):
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
    sim = http_request.parse_post(id=1, template=1)
    src = pkio.py_path(
        simulation_db.find_global_simulation(
            sim.type,
            sim.id,
            checked=True,
        ),
    )
    data = simulation_db.open_json_file(
        sim.type,
        src.join(simulation_db.SIMULATION_DATA_FILE),
    )
    data.pkdel('report')
    data.models.simulation.isExample = False
    data.models.simulation.outOfSessionSimulationId = sim.id
    res = _save_new_and_reply(data)
    sirepo.sim_data.get_class(sim_type).lib_files_from_other_user(
        data,
        simulation_db.lib_dir_from_sim_dir(src),
    )
    target = simulation_db.simulation_dir(sim.type, data.models.simulation.simulationId)
    if hasattr(sim.template, 'copy_related_files'):
        sim.template.copy_related_files(data, str(src), str(target))
    return res


@api_perm.require_user
def api_copySimulation():
    """Takes the specified simulation and returns a newly named copy with the suffix ( X)"""
    sim = http_request.parse_post(id=1)
#TODO(robnagler) add support for name and folder validation
    n = sim.req_data.name
    assert n, sirepo.util.err(sim, 'No name in request')
    d = simulation_db.read_simulation_json(sim.type, sid=sim.id)
    d.models.simulation.pkupdate(
        name=n,
        folder=sim.req_data.get('folder', '/'),
        isExample=False,
        outOfSessionSimulationId='',
    )
    return _save_new_and_reply(d)


@api_perm.require_user
def api_deleteFile():
    sim = http_request.parse_post(filename=1, file_type=1)
    e = _simulations_using_file(sim)
    if len(e):
        return http_reply.gen_json({
            'error': 'File is in use in other simulations.',
            'fileList': e,
            'fileName': sim.filename,
        })

    # Will not remove resource (standard) lib files
    pkio.unchecked_remove(_lib_file_write_path(sim))
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_deleteSimulation():
    sim = http_request.parse_post(id=1)
    simulation_db.delete_simulation(sim.type, sim.id)
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_downloadFile(simulation_type, simulation_id, filename):
#TODO(pjm): simulation_id is an unused argument
    sim = http_request.parse_params(type=simulation_type, filename=filename)
    n = sim.sim_data.lib_file_name_without_type(sim.filename)
    p = sim.sim_data.lib_file_abspath(sim.filename)
    try:
        return flask.send_file(
            str(p),
            as_attachment=True,
            attachment_filename=n,
        )
    except IOError as e:
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
    sim = http_request.parse_params(
        filename=filename,
        id=simulation_id,
        type=simulation_type,
    )
    from sirepo import exporter
    return exporter.create_archive(sim)


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
    sim = http_request.parse_params(type=simulation_type, file_type=file_type)
    return http_reply.gen_json(
        sim.sim_data.lib_files_name_for_type(sim.file_type),
    )


@api_perm.allow_visitor
def api_findByName(simulation_type, application_mode, simulation_name):
    sim = http_request.parse_params(type=simulation_type)
    return http_reply.gen_redirect_for_local_route(
        sim.type,
        'findByName',
        PKDict(
            applicationMode=application_mode,
            simulationName=simulation_name,
        ),
    )


@api_perm.require_user
def api_findByNameWithAuth(simulation_type, application_mode, simulation_name):
    sim = http_request.parse_params(type=simulation_type)
    #TODO(pjm): need to unquote when redirecting from saved cookie redirect?
    simulation_name = urllib.unquote(simulation_name)
    # use the existing named simulation, or copy it from the examples
    rows = simulation_db.iterate_simulation_datafiles(
        sim.type,
        simulation_db.process_simulation_list,
        {
            'simulation.name': simulation_name,
            'simulation.isExample': True,
        },
    )
    if len(rows) == 0:
        for s in simulation_db.examples(sim.type):
            if s['models']['simulation']['name'] != simulation_name:
                continue
            simulation_db.save_new_example(s)
            rows = simulation_db.iterate_simulation_datafiles(
                sim.type,
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
                sim.type,
            )
    m = simulation_db.get_schema(sim.type).appModes[application_mode]
    return http_reply.gen_redirect_for_local_route(
        sim.type,
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
    sim = http_request.parse_post(template=1)
    res = sim.template.get_application_data(sim.req_data)
    if filename:
        assert isinstance(res, _PY_PATH_LOCAL_CLASS), \
            '{}: template did not return a file'.format(res)
        return flask.send_file(
            str(res),
            mimetype='application/octet-stream',
            as_attachment=True,
            attachment_filename=werkzeug.secure_filename(filename),
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
        # special http_request parsing here
        template = simulation_type and sirepo.template.import_module(
            http_request.parse_params(type=simulation_type).type,
        )
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
            with simulation_db.tmp_dir() as d:
                data = template.import_file(flask.request, tmp_dir=d)
            if 'error' in data:
                return http_reply.gen_json(data)
            if 'version' in data:
                # this will force the fixups to run when saved
                del data['version']
        #TODO(robnagler) need to validate folder
        data.models.simulation.folder = flask.request.form['folder']
        data.models.simulation.isExample = False
        return _save_new_and_reply(data)
    except werkzeug.exceptions.HTTPException:
        raise
    except sirepo.util.Reply:
        raise
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
    sim = http_request.parse_post(template=1)
    d = simulation_db.default_data(sim.type)
#TODO(robnagler) assert values
#TODO(pjm): update fields from schema values across new_simulation_data values
    d.models.simulation.pkupdate(
        name=sim.req_data.name,
        folder=sim.req_data.folder,
        notes=sim.req_data.get('notes', ''),
    )
    if hasattr(sim.template, 'new_simulation'):
        sim.template.new_simulation(d, sim.req_data)
    return _save_new_and_reply(d)


@api_perm.require_user
def api_pythonSource(simulation_type, simulation_id, model=None, title=None):
    sim = http_request.parse_params(type=simulation_type, id=simulation_id, template=True)
    m = model and sim.sim_data.parse_model(model)
    d = simulation_db.read_simulation_json(sim.type, sid=sim.id)
    return _safe_attachment(
        flask.make_response(
            sim.template.python_source_for_model(d, m),
        ),
        d.models.simulation.name + ('-' + title if title else ''),
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
                for x in sorted(feature_config.cfg().sim_types)
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
        sim = http_request.parse_params(type=simulation_type)
    except AssertionError:
        if simulation_type == 'warp':
            return http_reply.gen_redirect(sirepo.uri.app_root('warppba'))
        if simulation_type == 'fete':
            return http_reply.gen_redirect(sirepo.uri.app_root('warpvnd'))
        sirepo.util.raise_not_found('Invalid simulation_type={}', simulation_type)
    return _render_root_page('index', PKDict(app_name=sim.type))


@api_perm.require_user
def api_saveSimulationData():
    # do not fixup_old_data yet
    sim = http_request.parse_post(id=1, template=1)
    d = sim.req_data
    simulation_db.validate_serial(d)
    d = simulation_db.fixup_old_data(d)[0]
    if hasattr(sim.template, 'prepare_for_save'):
        d = sim.template.prepare_for_save(d)
    d = simulation_db.save_simulation_json(d)
    return api_simulationData(
        d.simulationType,
        d.models.simulation.simulationId,
        pretty=False,
    )


@api_perm.require_user
def api_simulationData(simulation_type, simulation_id, pretty, section=None):
    """First entry point for a simulation

    Might be non-session simulation copy (see `simulation_db.CopyRedirect`).
    We have to allow a non-user to get data.
    """
    #TODO(robnagler) need real type transforms for inputs
    sim = http_request.parse_params(type=simulation_type, id=simulation_id, template=1)
    pretty = bool(int(pretty))
    try:
        d = simulation_db.read_simulation_json(sim.type, sid=sim.id)
        if hasattr(sim.template, 'prepare_for_client'):
            d = sim.template.prepare_for_client(d)
        resp = http_reply.gen_json(
            d,
            pretty=pretty,
        )
        if pretty:
            _safe_attachment(
                resp,
                d.models.simulation.name,
                'json',
            )
    except simulation_db.CopyRedirect as e:
        if e.sr_response['redirect'] and section:
            e.sr_response['redirect']['section'] = section
        resp = http_reply.gen_json(e.sr_response)
    return http_reply.headers_for_no_cache(resp)


@api_perm.require_user
def api_listSimulations():
    sim = http_request.parse_post()
    simulation_db.verify_app_directory(sim.type)
    return http_reply.gen_json(
        sorted(
            simulation_db.iterate_simulation_datafiles(
                sim.type,
                simulation_db.process_simulation_list,
                sim.req_data.get('search'),
            ),
            key=lambda row: row['name'],
        )
    )

@api_perm.require_user
def api_getServerData():
    input = http_request.parse_json()
#TODO(robnagler) validate
    id = input.id if 'id' in input else None
    d = adm.get_server_data(id)
    if d == None or len(d) == 0:
        raise sirepo.util.UserAlert('Data error', 'no data supplied')
    return http_reply.gen_json(d)


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
        sirepo.auth.init_mock()
    if v.want_cookie:
        import sirepo.cookie
        sirepo.cookie.set_sentinel()
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
    sim = http_request.parse_post()
#TODO(robnagler) validate
    old_name = sim.req_data['oldName']
    new_name = sim.req_data['newName']
    for row in simulation_db.iterate_simulation_datafiles(sim.type, _simulation_data):
        folder = row['models']['simulation']['folder']
        if folder.startswith(old_name):
            row['models']['simulation']['folder'] = re.sub(re.escape(old_name), new_name, folder, 1)
            simulation_db.save_simulation_json(row)
    return http_reply.gen_json_ok()


@api_perm.require_user
def api_uploadFile(simulation_type, simulation_id, file_type):
    f = flask.request.files['file']
    sim = http_request.parse_params(
        file_type=file_type,
        filename=f.filename,
        id=simulation_id,
        template=1,
        type=simulation_type,
    )
    e = None
    in_use = None
    with simulation_db.tmp_dir() as d:
        t = d.join(sim.filename)
        f.save(str(t))
        if hasattr(sim.template, 'validate_file'):
            e = sim.template.validate_file(sim.file_type, t)
        if (
            not e and sim.sim_data.lib_file_exists(sim.filename)
            and not flask.request.form.get('confirm')
        ):
            in_use = _simulations_using_file(sim, ignore_sim_id=sim.id)
            if in_use:
                e = 'File is in use in other simulations. Please confirm you would like to replace the file for all simulations.'
        if e:
            return http_reply.gen_json({
                'error': e,
                'filename': sim.filename,
                'fileList': in_use,
                'fileType': sim.file_type,
                'simulationId': sim.id,
            })
        t.rename(_lib_file_write_path(sim))
    return http_reply.gen_json({
        'filename': sim.filename,
        'fileType': sim.file_type,
        'simulationId': sim.id,
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
    _app.sirepo_db_dir = sirepo.srdb.root()
    _app.sirepo_uwsgi = uwsgi
    _app.sirepo_use_reloader = use_reloader
    uri_router.init(_app, simulation_db)
    return _app


def init_apis(app, *args, **kwargs):
    for e, _ in simulation_db.SCHEMA_COMMON['customErrors'].items():
        app.register_error_handler(int(e), _handle_error)
    importlib.import_module(
        'sirepo.' + ('job' if feature_config.cfg().job_supervisor else 'runner')
    ).init_by_server(app)


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


def _lib_file_write_path(sim):
    return sim.sim_data.lib_file_write_path(
        sim.sim_data.lib_file_name_with_type(sim.filename, sim.file_type),
    )


def _render_root_page(page, values):
    values.update(PKDict(
        app_version=simulation_db.app_version(),
        source_cache_key=_source_cache_key(),
        static_files=simulation_db.static_libs(),
    ))
    return http_reply.render_static(page, 'html', values, cache_ok=True)


def _safe_attachment(resp, base, suffix):
    return http_reply.as_attachment(
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


def _simulations_using_file(sim, ignore_sim_id=None):
    res = []
    for r in simulation_db.iterate_simulation_datafiles(sim.type, _simulation_data):
        if not sim.sim_data.lib_file_in_use(r, sim.filename):
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
    job_queue=pkconfig.ReplacedBy('sirepo.runner.job_class'),
)
