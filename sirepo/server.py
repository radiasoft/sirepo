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
from sirepo.template import adm
from sirepo import api_perm
from sirepo import feature_config
from sirepo import http_reply
from sirepo import http_request
from sirepo import runner
from sirepo import runner_client
from sirepo import simulation_db
from sirepo import srdb
from sirepo import uri_router
from sirepo import util
from sirepo.template import template_common
import datetime
import flask
import glob
import os.path
import py.path
import re
import sirepo.template
import sys
import time
import uuid
import werkzeug
import werkzeug.exceptions

#TODO(pjm): this import is required to work-around template loading in listSimulations, see #1151
if any(k in feature_config.cfg.sim_types for k in ('flash', 'rs4pi', 'synergia', 'warppba', 'warpvnd')):
    import h5py

#: class that py.path.local() returns
_PY_PATH_LOCAL_CLASS = type(pkio.py_path())

#: What is_running?
_RUN_STATES = ('pending', 'running')

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(r'(?:warning|exception|error): ([^\n]+?)(?:;|\n|$)', flags=re.IGNORECASE)

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
    data['models']['simulation']['isExample'] = False
    data['models']['simulation']['outOfSessionSimulationId'] = req['simulationId']
    res = _save_new_and_reply(data)
    target = simulation_db.simulation_dir(sim_type, simulation_db.parse_sid(data))
    template_common.copy_lib_files(
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
    assert name, util.err(req, 'No name in request')
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
    data = _parse_data_input()
    simulation_db.delete_simulation(data['simulationType'], data['simulationId'])
    return http_reply.gen_json_ok()


@api_perm.require_user
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


@api_perm.require_user
def api_downloadFile(simulation_type, simulation_id, filename):
    #TODO(pjm): simulation_id is an unused argument
    lib = simulation_db.simulation_lib_dir(simulation_type)
    filename = werkzeug.secure_filename(filename)
    p = lib.join(filename)
    if simulation_type == 'srw':
        attachment_name = filename
    else:
        # strip file_type prefix from attachment filename
        attachment_name = re.sub(r'^.*?-.*?\.', '', filename)
    return flask.send_file(str(p), as_attachment=True, attachment_filename=attachment_name)


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
    file_type = werkzeug.secure_filename(file_type)
    if simulation_type == 'srw':
        #TODO(pjm): special handling for srw, file_type not included in filename
        res = sirepo.template.import_module(simulation_type).get_file_list(file_type)
    else:
        res = []
        search = ['{}.*'.format(file_type)]
        d = simulation_db.simulation_lib_dir(simulation_type)
        for extension in search:
            for f in glob.glob(str(d.join(extension))):
                if os.path.isfile(f):
                    filename = os.path.basename(f)
                    # strip the file_type prefix
                    filename = filename[len(file_type) + 1:]
                    res.append(filename)
    res.sort()
    return http_reply.gen_json(res)


@api_perm.allow_cookieless_require_user
def api_findByName(simulation_type, application_mode, simulation_name):
    sim_type = sirepo.template.assert_sim_type(simulation_type)
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
            util.raise_not_found(
                'simulation not found by name={} type={}',
                simulation_name,
                sim_type,
            )
    # format the uri for the local route to this simulation for application_mode
    s = simulation_db.get_schema(sim_type)
    m = s.appModes[application_mode]
    r = m.localRoute
    assert r in s.localRoutes
    u = '/{}#/{}/{}'.format(sim_type, r, rows[0].simulationId)
    if m.includeMode:
        u += '?application_mode={}'.format(application_mode)
    return http_reply.gen_redirect_for_anchor(u)


@api_perm.require_user
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
    return _render_root_page('landing-page', pkcollections.Dict())


@api_perm.require_user
def api_newSimulation():
    new_simulation_data = _parse_data_input()
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


@api_perm.allow_visitor
def api_robotsTxt():
    """Disallow the app (dev, prod) or / (alpha, beta)"""
    global _ROBOTS_TXT
    if not _ROBOTS_TXT:
        # We include dev so we can test
        if pkconfig.channel_in('prod', 'dev'):
            u = [
                uri_router.uri_for_api('root', params={'simulation_type': x})
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
            return http_reply.gen_redirect_for_root('warppba', code=301)
        if simulation_type == 'fete':
            return http_reply.gen_redirect_for_root('warpvnd', code=301)
        pkdlog('{}: uri not found', simulation_type)
        util.raise_not_found('Invalid simulation_type: {}', simulation_type)
    values = pkcollections.Dict()
    values.app_name = simulation_type
    return _render_root_page('index', values)


@api_perm.require_user
def api_runCancel():
    data = _parse_data_input()
    jid = simulation_db.job_id(data)
    if feature_config.cfg.runner_daemon:
        jhash = template_common.report_parameters_hash(data)
        run_dir = simulation_db.simulation_run_dir(data)
        runner_client.cancel_report_job(run_dir, jhash)
        # Always true from the client's perspective
        return http_reply.gen_json({'state': 'canceled'})
    else:
        # TODO(robnagler) need to have a way of listing jobs
        # Don't bother with cache_hit check. We don't have any way of canceling
        # if the parameters don't match so for now, always kill.
        #TODO(robnagler) mutex required
        if runner.job_is_processing(jid):
            run_dir = simulation_db.simulation_run_dir(data)
            # Write first, since results are write once, and we want to
            # indicate the cancel instead of the termination error that
            # will happen as a result of the kill.
            simulation_db.write_result({'state': 'canceled'}, run_dir=run_dir)
            runner.job_kill(jid)
            # TODO(robnagler) should really be inside the template (t.cancel_simulation()?)
            # the last frame file may not be finished, remove it
            t = sirepo.template.import_module(data)
            if hasattr(t, 'remove_last_frame'):
                t.remove_last_frame(run_dir)
        # Always true from the client's perspective
        return http_reply.gen_json({'state': 'canceled'})


@api_perm.require_user
def api_runSimulation():
    from pykern import pkjson
    data = _parse_data_input(validate=True)
    # if flag is set
    # - check status
    # - if status is bad, rewrite the run dir (XX race condition, to fix later)
    # - then request it be started
    if feature_config.cfg.runner_daemon:
        jhash = template_common.report_parameters_hash(data)
        run_dir = simulation_db.simulation_run_dir(data)
        status = runner_client.report_job_status(run_dir, jhash)
        already_good_status = [runner_client.JobStatus.RUNNING,
                               runner_client.JobStatus.COMPLETED]
        if status not in already_good_status:
            data['simulationStatus'] = {
                'startTime': int(time.time()),
                'state': 'pending',
            }
            tmp_dir = run_dir + '-' + jhash + '-' + uuid.uuid4() + srdb.TMP_DIR_SUFFIX
            cmd, _ = simulation_db.prepare_simulation(data, tmp_dir=tmp_dir)
            runner_client.start_report_job(run_dir, jhash, cfg.backend, cmd, tmp_dir)
        res = _simulation_run_status_runner_daemon(data, quiet=True)
        return http_reply.gen_json(res)
    else:
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
        return http_reply.gen_json(res)


@api_perm.require_user
def api_runStatus():
    data = _parse_data_input()
    if feature_config.cfg.runner_daemon:
        status = _simulation_run_status_runner_daemon(data)
    else:
        status = _simulation_run_status(data)
    return http_reply.gen_json(status)


@api_perm.require_user
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
        err_redirect = _verify_user_dir(simulation_type)
        if err_redirect:
            return err_redirect
        data = simulation_db.read_simulation_json(simulation_type, sid=simulation_id)
        template = sirepo.template.import_module(simulation_type)
        if hasattr(template, 'prepare_for_client'):
            data = template.prepare_for_client(data)
        resp = http_reply.gen_json(
            data,
            pretty=pretty,
        )
        if pretty:
            _as_attachment(
                resp,
                http_reply.MIME_TYPE.json,
                '{}.json'.format(data.models.simulation.name),
            )
    except simulation_db.CopyRedirect as e:
        if e.sr_response['redirect'] and section:
            e.sr_response['redirect']['section'] = section
        resp = http_reply.gen_json(e.sr_response)
    return http_reply.headers_for_no_cache(resp)


@api_perm.require_user
def api_simulationFrame(frame_id):
    #TODO(robnagler) startTime is reportParametersHash; need version on URL and/or param names in URL
    keys = ['simulationType', 'simulationId', 'modelName', 'animationArgs', 'frameIndex', 'startTime']
    data = dict(zip(keys, frame_id.split('*')))
    template = sirepo.template.import_module(data)
    data['report'] = template.get_animation_name(data)
    run_dir = simulation_db.simulation_run_dir(data)
    model_data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if feature_config.cfg.runner_daemon:
        # XX TODO: it would be better if the frontend passed the jhash to this
        # call. Since it doesn't, we have to read it out of the run_dir, which
        # creates a race condition -- we might return a frame from a different
        # version of the report than the one the frontend expects.
        jhash = template_common.report_parameters_hash(model_data)
        frame = runner_client.run_extract_job(
            run_dir, jhash, 'get_simulation_frame', data,
        )
    else:
        frame = template.get_simulation_frame(run_dir, data, model_data)
    resp = http_reply.gen_json(frame)
    if 'error' not in frame and template.WANT_BROWSER_FRAME_CACHE:
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(365)
        resp.headers['Cache-Control'] = 'public, max-age=31536000'
        resp.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        resp.headers['Last-Modified'] = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    else:
        http_reply.headers_for_no_cache(resp)
    return resp


@api_perm.require_user
def api_listSimulations():
    data = _parse_data_input()
    sim_type = data['simulationType']
    search = data['search'] if 'search' in data else None
    err_redirect = _verify_user_dir(sim_type)
    if err_redirect:
        return http_reply.gen_json({
            'state': 'error',
            'errorRedirect': err_redirect.headers.get('Location'),
        })
    simulation_db.verify_app_directory(sim_type)
    return http_reply.gen_json(
        sorted(
            simulation_db.iterate_simulation_datafiles(sim_type, simulation_db.process_simulation_list, search),
            key=lambda row: row['name'],
        )
    )

@api_perm.require_user
def api_getServerData():
    input = _parse_data_input(False)
    id = input.id if 'id' in input else None
    d = adm.get_server_data(id)
    if d == None or len(d) == 0:
        return _simulation_error('Data error')
    return http_reply.gen_json(d)


# visitor rather than user because error pages are rendered by the application
@api_perm.allow_visitor
def api_simulationSchema():
    sim_type = sirepo.template.assert_sim_type(flask.request.form['simulationType'])
    return http_reply.gen_json(simulation_db.get_schema(sim_type))


@api_perm.allow_visitor
def api_srwLight():
    return _render_root_page('light', pkcollections.Dict())


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
    data = _parse_data_input()
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
            err = template.validate_file(file_type, str(p))
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
    http_reply.init_by_server(_app)
    simulation_db.init_by_server(_app)
    uri_router.init(_app)
    for e, _ in simulation_db.SCHEMA_COMMON['customErrors'].items():
        _app.register_error_handler(int(e), _handle_error)
    runner.init(_app, use_reloader)
    return _app


def init_apis(*args, **kwargs):
    pass


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


def _parse_data_input(validate=False):
    data = http_request.parse_json(assert_sim_type=False)
    return simulation_db.fixup_old_data(data)[0] if validate else data


def _render_root_page(page, values):
    values.update(pkcollections.Dict(
        app_version=simulation_db.app_version(),
        source_cache_key=_source_cache_key(),
        static_files=simulation_db.static_libs(),
    ))
    return http_reply.render_static(page, 'html', values, cache_ok=True)


def _save_new_and_reply(*args):
    data = simulation_db.save_new_simulation(*args)
    return api_simulationData(
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


def _simulation_run_status_runner_daemon(data, quiet=False):
    """Look for simulation status and output

    Args:
        data (dict): request
        quiet (bool): don't write errors to log

    Returns:
        dict: status response
    """
    try:
        run_dir = simulation_db.simulation_run_dir(data)
        jhash = template_common.report_parameters_hash(data)
        status = runner_client.report_job_status(run_dir, jhash)
        is_running = status is runner_client.JobStatus.RUNNING
        rep = simulation_db.report_info(data)
        res = {'state': status.value}

        if not is_running:
            if status is not runner_client.JobStatus.MISSING:
                res, err = runner_client.run_extract_job(
                    run_dir, jhash, 'result', data,
                )
                if err:
                    return _simulation_error(err, 'error in read_result', run_dir)
        if simulation_db.is_parallel(data):
            new = runner_client.run_extract_job(
                run_dir,
                jhash,
                'background_percent_complete',
                is_running,
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
        if is_running:
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
            is_running,
            res['state'],
            rep.cache_hit,
            rep.cached_hash,
            rep.req_hash,
        )
    except Exception:
        return _simulation_error(pkdexc(), quiet=quiet)
    return res


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
        is_processing = runner.job_is_processing(rep.job_id)
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
            runner.job_race_condition_reap(rep.job_id)
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
                    template.prepare_output_file(rep.run_dir, data)
                res2, err = simulation_db.read_result(rep.run_dir)
                if err:
                    if simulation_db.is_parallel(data):
                        # allow parallel jobs to use template to parse errors below
                        res['state'] = 'error'
                    else:
                        if hasattr(template, 'parse_error_log'):
                            res = template.parse_error_log(rep.run_dir)
                            if res:
                                return res
                        return _simulation_error(err, 'error in read_result', rep.run_dir)
                else:
                    res = res2
        if simulation_db.is_parallel(data):
            new = template.background_percent_complete(
                rep.model_name,
                rep.run_dir,
                is_running,
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
    runner.job_start(data)


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
        pkdlog('Force log out, user has no user_dir: {}', uid)
        #TODO(pjm): call http_reply to format route?
        return flask.redirect('/auth-logout/' + sim_type)
    return None


def static_dir(dir_name):
    return str(simulation_db.STATIC_FOLDER.join(dir_name))


cfg = pkconfig.init(
    db_dir=(None, _cfg_db_dir, 'DEPRECATED: set $SIREPO_SRDB_ROOT'),
    job_queue=(None, str, 'DEPRECATED: set $SIREPO_RUNNER_JOB_CLASS'),
    enable_source_cache_key=(True, bool, 'enable source cache key, disable to allow local file edits in Chrome'),
    backend=('local', str, 'Select runner daemon backend (e.g. "local", "docker")'),
)
