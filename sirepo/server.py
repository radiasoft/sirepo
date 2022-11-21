# -*- coding: utf-8 -*-
"""Flask server interface

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import simulation_db
import re
import sirepo.feature_config
import sirepo.flask
import sirepo.quest
import sirepo.resource
import sirepo.sim_data
import sirepo.srschema
import sirepo.uri
import sirepo.util
import urllib
import urllib.parse
import werkzeug
import werkzeug.exceptions


# TODO(pjm): this import is required to work-around template loading in listSimulations, see #1151
if any(
    k in sirepo.feature_config.cfg().sim_types
    for k in ("flash", "rs4pi", "radia", "synergia", "silas", "warppba", "warpvnd")
):
    import h5py

#: If google_tag_manager_id set, string to insert in landing pages for google analytics
_google_tag_manager = None

#: what to match in landing pages to insert `_google_tag_manager`
_google_tag_manager_re = re.compile("(?=</head>)", flags=re.IGNORECASE)

#: See sirepo.srunit
SRUNIT_TEST_IN_REQUEST = "srunit_test_in_request"

#: Default file to serve on errors
DEFAULT_ERROR_FILE = "server-error.html"

_ROBOTS_TXT = None

#: Global app value (only here so instance not lost)
_app = None

#: See `_proxy_react`
_PROXY_REACT_URI_SET = None

#: See `_proxy_react`
_PROXY_REACT_URI_RE = None

#: See `_proxy_react`
_REACT_SERVER_BUILD = "build"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_user", sid="SimId")
    def api_copyNonSessionSimulation(self):
        req = self.parse_post(id=True, template=True)
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
        data.pkdel("report")
        data.models.simulation.isExample = False
        data.models.simulation.outOfSessionSimulationId = req.id
        res = self._save_new_and_reply(req, data)
        sirepo.sim_data.get_class(req.type).lib_files_from_other_user(
            data,
            simulation_db.lib_dir_from_sim_dir(src),
            qcall=self,
        )
        target = simulation_db.simulation_dir(
            req.type,
            data.models.simulation.simulationId,
            qcall=self,
        )
        # TODO(robnagler) does not work, supervisor needs to be notified to
        # copy the simulation state.
        # if hasattr(req.template, 'copy_related_files'):
        #     req.template.copy_related_files(data, str(src), str(target))
        return res

    @sirepo.quest.Spec(
        "require_user", sid="SimId", folder="SimFolderName", name="SimName"
    )
    def api_copySimulation(self):
        """Takes the specified simulation and returns a newly named copy with the suffix ( X)"""
        req = self.parse_post(id=True, folder=True, name=True, template=True)
        d = simulation_db.read_simulation_json(req.type, sid=req.id, qcall=self)
        d.models.simulation.pkupdate(
            name=req.name,
            folder=req.folder,
            isExample=False,
            outOfSessionSimulationId="",
        )
        return self._save_new_and_reply(req, d)

    @sirepo.quest.Spec("require_user", filename="SimFileName", file_type="SimFileType")
    def api_deleteFile(self):
        req = self.parse_post(filename=True, file_type=True)
        e = _simulations_using_file(req)
        if len(e):
            return self.reply_json(
                {
                    "error": "File is in use in other simulations.",
                    "fileList": e,
                    "fileName": req.filename,
                }
            )

        # Will not remove resource (standard) lib files
        pkio.unchecked_remove(_lib_file_write_path(req))
        return self.reply_ok()

    @sirepo.quest.Spec("require_user", sid="SimId")
    def api_deleteSimulation(self):
        req = self.parse_post(id=True)
        simulation_db.delete_simulation(req.type, req.id, qcall=self)
        return self.reply_ok()

    @sirepo.quest.Spec(
        "require_user", sid="SimId optional", filename="SimFileName", sim_data="SimData"
    )
    def api_downloadFile(self, simulation_type, simulation_id, filename):
        # TODO(pjm): simulation_id is an unused argument
        req = self.parse_params(type=simulation_type, filename=filename)
        n = req.sim_data.lib_file_name_without_type(req.filename)
        p = req.sim_data.lib_file_abspath(req.filename, qcall=self)
        try:
            return self.reply_attachment(p, filename=n)
        except Exception as e:
            if pkio.exception_is_not_found(e):
                sirepo.util.raise_not_found("lib_file={} not found", p)
            raise

    @sirepo.quest.Spec("allow_visitor", spec="ErrorLoggingSpec")
    def api_errorLogging(self):
        ip = self.sreq.remote_addr
        try:
            pkdlog(
                "{}: javascript error: {}",
                ip,
                simulation_db.generate_json(self.parse_json(), pretty=True),
            )
        except Exception as e:
            pkdlog(
                "ip={}: error parsing javascript exception={} input={}",
                ip,
                e,
                self.sreq.internal_req.data
                and self.sreq.internal_req.data.decode("unicode-escape"),
            )
        return self.reply_ok()

    @sirepo.quest.Spec(
        "require_user", simulation_id="SimId", filename="SimExportFileName"
    )
    def api_exportArchive(self, simulation_type, simulation_id, filename):
        req = self.parse_params(
            template=True,
            filename=filename,
            id=simulation_id,
            type=simulation_type,
        )
        from sirepo import exporter

        return exporter.create_archive(req, self)

    @sirepo.quest.Spec("allow_visitor")
    def api_favicon(self):
        """Routes to favicon.ico file."""
        # SECURITY: We control the path of the file so using send_file is ok.
        return self.reply_file(
            sirepo.resource.static("img", "favicon.ico"),
            content_type="image/vnd.microsoft.icon",
        )

    @sirepo.quest.Spec("allow_visitor")
    def api_forbidden(self):
        sirepo.util.raise_forbidden("app forced forbidden")

    @sirepo.quest.Spec(
        "require_user",
        sid="SimId deprecated",
        file_type="LibFileType",
        sim_data="SimData",
    )
    def api_listFiles(self, simulation_type, simulation_id, file_type):
        # TODO(pjm): simulation_id is an unused argument
        req = self.parse_params(type=simulation_type, file_type=file_type)
        return self.reply_json(
            req.sim_data.lib_file_names_for_type(req.file_type, qcall=self),
        )

    @sirepo.quest.Spec(
        "allow_visitor", application_mode="AppMode", simulation_name="SimName"
    )
    def api_findByName(self, simulation_type, application_mode, simulation_name):
        req = self.parse_params(type=simulation_type)
        return self.reply_redirect_for_local_route(
            req.type,
            "findByName",
            PKDict(
                applicationMode=application_mode,
                simulationName=simulation_name,
            ),
        )

    @sirepo.quest.Spec(
        "require_user", application_mode="AppMode", simulation_name="SimName"
    )
    def api_findByNameWithAuth(
        self, simulation_type, application_mode, simulation_name
    ):
        req = self.parse_params(type=simulation_type)
        # TODO(pjm): need to unquote when redirecting from saved cookie redirect?
        simulation_name = urllib.parse.unquote(simulation_name)
        # use the existing named simulation, or copy it from the examples
        rows = simulation_db.iterate_simulation_datafiles(
            req.type,
            simulation_db.process_simulation_list,
            {
                "simulation.name": simulation_name,
                "simulation.isExample": True,
            },
            qcall=self,
        )
        if len(rows) == 0:
            for s in simulation_db.examples(req.type):
                if s["models"]["simulation"]["name"] != simulation_name:
                    continue
                simulation_db.save_new_example(s, qcall=self)
                rows = simulation_db.iterate_simulation_datafiles(
                    req.type,
                    simulation_db.process_simulation_list,
                    {
                        "simulation.name": simulation_name,
                    },
                    qcall=self,
                )
                break
            else:
                sirepo.util.raise_not_found(
                    "simulation not found by name={} type={}",
                    simulation_name,
                    req.type,
                )
        m = simulation_db.get_schema(req.type).appModes[application_mode]
        return self.reply_redirect_for_local_route(
            req.type,
            m.localRoute,
            PKDict(simulationId=rows[0].simulationId),
            query=m.includeMode and PKDict(application_mode=application_mode),
        )

    @sirepo.quest.Spec(
        "require_user", filename="SimFileName", spec="ApplicationDataSpec"
    )
    def api_getApplicationData(self, filename=None):
        """Get some data from the template

        Args:
            filename (str): if supplied, result is file attachment

        Returns:
            response: may be a file or JSON
        """
        req = self.parse_post(template=True, filename=filename or None)
        with simulation_db.tmp_dir(qcall=self) as d:
            assert "method" in req.req_data
            res = req.template.get_application_data(req.req_data, qcall=self, tmp_dir=d)
            assert (
                res != None
            ), f"unhandled application data method: {req.req_data.method}"
            if "filename" in req and isinstance(res, pkconst.PY_PATH_LOCAL_TYPE):
                return self.reply_attachment(
                    res,
                    filename=req.filename,
                    content_type=req.req_data.get("contentType", None),
                )
            return self.reply_json(res)

    @sirepo.quest.Spec(
        "require_user",
        file="ImportFile",
        folder="SimFolderPath",
        sid="SimId",
        arguments="ImportArgs optional",
    )
    def api_importFile(self, simulation_type):
        """
        Args:
            simulation_type (str): which simulation type
        Params:
            file: file data
            folder: where to import to
        """
        from sirepo import importer

        error = None
        f = None

        try:
            f = self.sreq.internal_req.files.get("file")
            if not f:
                raise sirepo.util.Error(
                    "must supply a file",
                    "no file in request={}",
                    self.sreq.internal_req.data,
                )
            req = self.parse_params(
                filename=f.filename,
                folder=self.sreq.internal_req.form.get("folder"),
                id=self.sreq.internal_req.form.get("simulationId"),
                template=True,
                type=simulation_type,
            )
            req.file_stream = f.stream
            req.import_file_arguments = self.sreq.internal_req.form.get("arguments", "")

            def s(data):
                data.models.simulation.folder = req.folder
                data.models.simulation.isExample = False
                return self._save_new_and_reply(req, data)

            if pkio.has_file_extension(req.filename, "json"):
                data = importer.read_json(req.file_stream.read(), self, req.type)
            # TODO(pjm): need a separate URI interface to importer, added exception for rs4pi for now
            # (dicom input is normally a zip file)
            elif pkio.has_file_extension(req.filename, "zip") and req.type != "rs4pi":
                data = importer.read_zip(
                    req.file_stream.read(), self, sim_type=req.type
                )
            else:
                if not hasattr(req.template, "import_file"):
                    raise sirepo.util.Error(
                        "Only zip files are supported",
                        "no import_file in template req={}",
                        req,
                    )
                with simulation_db.tmp_dir(qcall=self) as d:
                    data = req.template.import_file(
                        req,
                        tmp_dir=d,
                        reply_op=s,
                        qcall=self,
                    )
                if "error" in data:
                    return self.reply_json(data)
            return s(data)
        except werkzeug.exceptions.HTTPException:
            raise
        except sirepo.util.Reply:
            raise
        except Exception as e:
            pkdlog("{}: exception: {}", f and f.filename, pkdexc())
            # TODO(robnagler) security issue here. Really don't want to report errors to user
            if hasattr(e, "args"):
                if len(e.args) == 1:
                    error = str(e.args[0])
                else:
                    error = str(e.args)
            else:
                error = str(e)
        return self.reply_json(
            {
                "error": error if error else "An unknown error occurred",
            }
        )

    @sirepo.quest.Spec("allow_visitor", path_info="PathInfo optional")
    def api_homePage(self, path_info=None):
        return self.call_api(
            "staticFile", kwargs=PKDict(path_info="en/" + (path_info or "landing.html"))
        )

    @sirepo.quest.Spec(
        "require_user",
        simulation_id="SimId",
        model="Model optional",
        title="DownloadNamePostfix optional",
    )
    def api_exportJupyterNotebook(
        self, simulation_type, simulation_id, model=None, title=None
    ):
        def _filename(req):
            res = d.models.simulation.name
            if req.title:
                res += "-" + sirepo.srschema.parse_name(title)
            return res + ".ipynb"

        def _data(req):
            f = getattr(req.template, "export_jupyter_notebook", None)
            if not f:
                sirepo.util.raise_not_found(f"API not supported for tempate={req.type}")
            return f(
                simulation_db.read_simulation_json(req.type, sid=req.id, qcall=self),
                qcall=self,
            )

        req = self.parse_params(type=simulation_type, id=simulation_id, template=True)
        return self.reply_attachment(
            _data(req),
            filename=_filename(req),
            content_type="application/json",
        )

    @sirepo.quest.Spec("require_user", folder="FolderName", name="SimName")
    def api_newSimulation(self):
        req = self.parse_post(template=True, folder=True, name=True)
        d = simulation_db.default_data(req.type)
        d.models.simulation.pkupdate(
            {k: v for k, v in req.req_data.items() if k in d.models.simulation}
        )
        d.models.simulation.pkupdate(
            name=req.name,
            folder=req.folder,
        )
        if hasattr(req.template, "new_simulation"):
            req.template.new_simulation(d, req.req_data, qcall=self)
        return self._save_new_and_reply(req, d)

    @sirepo.quest.Spec("allow_visitor")
    def api_notFound(self):
        sirepo.util.raise_not_found("app forced not found (uri parsing error)")

    @sirepo.quest.Spec(
        "require_user",
        simulation_id="SimId",
        model="ComputeModelName optional",
        title="DownloadNamePostfix optional",
    )
    def api_pythonSource(self, simulation_type, simulation_id, model=None, title=None):
        req = self.parse_params(type=simulation_type, id=simulation_id, template=True)
        m = model and req.sim_data.parse_model(model)
        d = simulation_db.read_simulation_json(req.type, sid=req.id, qcall=self)
        suffix = simulation_db.get_schema(
            simulation_type
        ).constants.simulationSourceExtension
        return self.reply_attachment(
            req.template.python_source_for_model(d, model=m, qcall=self),
            "{}.{}".format(
                d.models.simulation.name + ("-" + title if title else ""),
                "madx" if m == "madx" else suffix,
            ),
        )

    @sirepo.quest.Spec("allow_visitor")
    def api_robotsTxt(self):
        """Disallow the app (dev, prod) or / (alpha, beta)"""
        global _ROBOTS_TXT
        if not _ROBOTS_TXT:
            # We include dev so we can test
            if pkconfig.channel_in("prod", "dev"):
                u = [
                    self.uri_for_app_root(x)
                    for x in sorted(sirepo.feature_config.cfg().sim_types)
                ]
            else:
                u = ["/"]
            _ROBOTS_TXT = "".join(
                ["User-agent: *\n"] + ["Disallow: {}\n".format(x) for x in u],
            )
        return self.reply(_ROBOTS_TXT, content_type="text/plain")

    @sirepo.quest.Spec("allow_visitor", path_info="PathInfo")
    def api_root(self, path_info):
        from sirepo import template

        self._proxy_react(path_info)
        if path_info is None:
            return self.reply_redirect(cfg.home_page_uri)
        if template.is_sim_type(path_info):
            return self._render_root_page("index", PKDict(app_name=path_info))
        u = sirepo.uri.unchecked_root_redirect(path_info)
        if u:
            return self.reply_redirect(u)
        sirepo.util.raise_not_found(f"unknown path={path_info}")

    @sirepo.quest.Spec("require_user", sid="SimId", data="SimData all_input")
    def api_saveSimulationData(self):
        # do not fixup_old_data yet
        req = self.parse_post(id=True, template=True)
        d = req.req_data
        simulation_db.validate_serial(d, qcall=self)
        return self._simulation_data_reply(
            req,
            simulation_db.save_simulation_json(
                d, fixup=True, modified=True, qcall=self
            ),
        )

    @sirepo.quest.Spec(
        "require_user", simulation_id="SimId", pretty="Bool optional", section="Section"
    )
    def api_simulationData(
        self, simulation_type, simulation_id, pretty=False, section=None
    ):
        """First entry point for a simulation

        Might be non-session simulation copy (see `simulation_db.CopyRedirect`).
        We have to allow a non-user to get data.
        """

        def _not_found(req):
            if not simulation_db.find_global_simulation(req.type, req.id):
                sirepo.util.raise_not_found(
                    "stype={} sid={} global simulation not found", req.type, req.id
                )
            return self.headers_for_no_cache(self.reply_json(_redirect(req)))

        def _redirect(req):
            return PKDict(
                # only parsed by sirepo.js appstate.loadModesl
                notFoundCopyRedirect=PKDict(
                    section=section or "",
                    simulationId=req.id,
                    userCopySimulationId=simulation_db.find_user_simulation_copy(
                        sim_type=req.type,
                        sid=req.id,
                        qcall=self,
                    ),
                ),
            )

        # TODO(pjm): pretty is an unused argument
        # TODO(robnagler) need real type transforms for inputs
        req = self.parse_params(type=simulation_type, id=simulation_id, template=True)
        try:
            d = simulation_db.read_simulation_json(req.type, sid=req.id, qcall=self)
            return self._simulation_data_reply(req, d)
        except sirepo.util.SPathNotFound:
            return _not_found(req)

    @sirepo.quest.Spec("require_user", search="SearchSpec")
    def api_listSimulations(self):
        req = self.parse_post()
        return self.reply_json(
            sorted(
                simulation_db.iterate_simulation_datafiles(
                    req.type,
                    simulation_db.process_simulation_list,
                    req.req_data.get("search"),
                    qcall=self,
                ),
                key=lambda row: row["name"],
            )
        )

    # visitor rather than user because error pages are rendered by the application
    @sirepo.quest.Spec("allow_visitor")
    def api_simulationSchema(self):
        return self.reply_json(
            simulation_db.get_schema(
                self.parse_params(
                    type=self.sreq.internal_req.form["simulationType"],
                ).type,
            ),
        )

    @sirepo.quest.Spec("allow_visitor")
    def api_srwLight(self):
        return self._render_root_page("light", PKDict())

    @sirepo.quest.Spec("allow_visitor")
    def api_srUnit(self):
        v = getattr(sirepo.flask.app(), SRUNIT_TEST_IN_REQUEST)
        if v.want_user:
            self.cookie.set_sentinel()
            self.auth.login(is_mock=True)
        if v.want_cookie:
            self.cookie.set_sentinel()
        v.op(self)
        return self.reply_ok()

    @sirepo.quest.Spec("allow_visitor", path_info="FilePath")
    def api_staticFile(self, path_info=None):
        """Send file from static folder.

        Args:
            path_info (str): relative path to join
        Returns:
            Response: reply with file
        """
        if not path_info:
            sirepo.util.raise_not_found("empty path info")
        self._proxy_react("static/" + path_info)
        p = sirepo.resource.static(sirepo.util.safe_path(path_info))
        if _google_tag_manager and re.match(r"^en/[^/]+html$", path_info):
            return self.headers_for_cache(
                self.reply(
                    _google_tag_manager_re.sub(
                        _google_tag_manager,
                        pkio.read_text(p),
                    ),
                ),
                path=p,
            )
        if re.match(r"^(html|en)/[^/]+html$", path_info):
            return self.reply_html(p)
        return self.reply_file(p)

    @sirepo.quest.Spec("require_user", oldName="SimFolderPath", newName="SimFolderPath")
    def api_updateFolder(self):
        # TODO(robnagler) Folder should have a serial, or should it be on data
        req = self.parse_post()
        o = sirepo.srschema.parse_folder(req.req_data["oldName"])
        if o == "/":
            raise sirepo.util.Error(
                'cannot rename root ("/") folder',
                "old folder is root req={}",
                req,
            )
        n = sirepo.srschema.parse_folder(req.req_data["newName"])
        if n == "/":
            raise sirepo.util.Error(
                'cannot rename folder to root ("/")',
                "new folder is root req={}",
                req,
            )
        for r in simulation_db.iterate_simulation_datafiles(
            req.type,
            _simulation_data_iterator,
            qcall=self,
        ):
            f = r.models.simulation.folder
            l = o.lower()
            if f.lower() == o.lower():
                r.models.simulation.folder = n
            elif f.lower().startswith(o.lower() + "/"):
                r.models.simulation.folder = n + f[len() :]
            else:
                continue
            simulation_db.save_simulation_json(r, fixup=False, qcall=self)
        return self.reply_ok()

    @sirepo.quest.Spec(
        "require_user",
        file="LibFile",
        file_type="LibFileType",
        simulation_id="SimId",
        confirm="Bool optional",
    )
    def api_uploadFile(self, simulation_type, simulation_id, file_type):
        f = self.sreq.internal_req.files["file"]
        req = self.parse_params(
            file_type=file_type,
            filename=f.filename,
            id=simulation_id,
            template=True,
            type=simulation_type,
        )
        e = None
        in_use = None
        with simulation_db.tmp_dir(qcall=self) as d:
            t = d.join(req.filename)
            f.save(str(t))
            if hasattr(req.template, "validate_file"):
                # Note: validate_file may modify the file
                e = req.template.validate_file(req.file_type, t)
            if (
                not e
                and req.sim_data.lib_file_exists(req.filename, qcall=self)
                and not self.sreq.internal_req.form.get("confirm")
            ):
                in_use = _simulations_using_file(req, ignore_sim_id=req.id)
                if in_use:
                    e = "File is in use in other simulations. Please confirm you would like to replace the file for all simulations."
            if e:
                return self.reply_json(
                    {
                        "error": e,
                        "filename": req.filename,
                        "fileList": in_use,
                        "fileType": req.file_type,
                        "simulationId": req.id,
                    }
                )
            t.rename(_lib_file_write_path(req))
        return self.reply_json(
            {
                "filename": req.filename,
                "fileType": req.file_type,
                "simulationId": req.id,
            }
        )

    def _proxy_react(self, path):
        import requests

        def _build():
            if re.search(r"^react/\w+$", path):
                p = "index.html"
            elif path in cfg.react_sim_types:
                raise sirepo.util.Redirect(f"/react/{path}")
            else:
                p = path
            # call call api due to recursion of proxy_react
            raise sirepo.util.Response(
                flask.send_file(
                    sirepo.resource.static(sirepo.util.safe_path(f"react/{p}")),
                    conditional=True,
                ),
            )

        def _dev():
            r = requests.get(cfg.react_server + path)
            # We want to throw an exception here, because it shouldn't happen
            r.raise_for_status()
            raise sirepo.util.Response(self.reply_as_proxy(r))

        if not path or not cfg.react_server:
            return
        if path in _PROXY_REACT_URI_SET or _PROXY_REACT_URI_RE.search(path):
            _build() if cfg.react_server == _REACT_SERVER_BUILD else _dev()

    def _render_root_page(self, page, values):
        values.update(
            PKDict(
                app_version=simulation_db.app_version(),
                source_cache_key=_source_cache_key(),
                static_files=simulation_db.static_libs(),
            )
        )
        return self.reply_static_jinja(page, "html", values, cache_ok=True)

    def _save_new_and_reply(self, req, data):
        return self._simulation_data_reply(
            req,
            simulation_db.save_new_simulation(data, qcall=self),
        )

    def _simulation_data_reply(self, req, data):
        if hasattr(req.template, "prepare_for_client"):
            d = req.template.prepare_for_client(data, qcall=self)
        return self.headers_for_no_cache(self.reply_json(data))


def init_apis(*args, **kwargs):
    pass


def init_app(uwsgi=None, use_reloader=False, is_server=False):
    """Initialize globals and populate simulation dir"""
    import flask

    global _app

    if _app:
        return
    #: Flask app instance, must be bound globally
    _app = flask.Flask(
        __name__,
        static_folder=None,
    )
    _app.sirepo_uwsgi = uwsgi
    _app.sirepo_use_reloader = use_reloader
    for e, _ in simulation_db.SCHEMA_COMMON["customErrors"].items():
        _app.register_error_handler(int(e), _handle_error)
    _init_proxy_react()
    sirepo.modules.import_and_init("sirepo.uri_router").init_for_flask(_app)
    sirepo.flask.app_set(_app)
    if is_server:
        global _google_tag_manager
        from sirepo import auth_db

        with sirepo.quest.start() as qcall:
            auth_db.create_or_upgrade(qcall=qcall)

        if cfg.google_tag_manager_id:
            _google_tag_manager = f"""<script>
        (function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','{cfg.google_tag_manager_id}');
        </script>"""

        # Avoid unnecessary logging
        sirepo.flask.is_server = True
    return _app


def init_module(**imports):
    pass


def _cfg_react_server(value):
    if value is None:
        return None
    if not pkconfig.channel_in("dev"):
        pkconfig.raise_error("invalid channel={}; must be dev", pkconfig.cfg.channel)
    if value == _REACT_SERVER_BUILD:
        return value
    u = urllib.parse.urlparse(value)
    if (
        u.scheme
        and u.netloc
        and u.path == "/"
        and len(u.params + u.query + u.fragment) == 0
    ):
        return value
    pkconfig.raise_error(f"invalid url={value}, must be http://netloc/")


def _handle_error(error):
    status_code = 500
    if isinstance(error, werkzeug.exceptions.HTTPException):
        status_code = error.code
    try:
        error_file = simulation_db.SCHEMA_COMMON["customErrors"][str(status_code)][
            "url"
        ]
    except Exception:
        error_file = DEFAULT_ERROR_FILE
    return (
        # SECURITY: We control the path of the file so using send_file is ok.
        sirepo.flask.send_file(
            str(sirepo.resource.static("html", error_file)),
            mimetype="text/html",
            conditional=True,
        ),
        status_code,
    )


def _init_proxy_react():
    if not cfg.react_server:
        return
    global _PROXY_REACT_URI_RE, _PROXY_REACT_URI_SET
    p = [
        "asset-manifest.json",
        "manifest.json",
        "static/js/bundle.js",
        "static/js/bundle.js.map",
    ]
    for x in cfg.react_sim_types:
        p.append(x)
        p.append(f"{x}-schema.json")
    _PROXY_REACT_URI_SET = set(p)
    r = "^react/"
    if cfg.react_server == _REACT_SERVER_BUILD:
        r += r"|^static/(css|js)/main\."
    _PROXY_REACT_URI_RE = re.compile(r)


def _lib_file_write_path(req):
    return req.sim_data.lib_file_write_path(
        req.sim_data.lib_file_name_with_type(req.filename, req.file_type),
        qcall=req.qcall,
    )


def _simulation_data_iterator(res, path, data):
    """Iterator function to return entire simulation data"""
    res.append(data)


def _simulations_using_file(req, ignore_sim_id=None):
    res = []
    for r in simulation_db.iterate_simulation_datafiles(
        req.type,
        _simulation_data_iterator,
        qcall=req.qcall,
    ):
        if not req.sim_data.lib_file_in_use(r, req.filename):
            continue
        s = r.models.simulation
        if s.simulationId == ignore_sim_id:
            continue
        res.append(
            "{}{}{}".format(
                s.folder,
                "" if s.folder == "/" else "/",
                s.name,
            )
        )
    return res


def _source_cache_key():
    if cfg.enable_source_cache_key:
        return "?{}".format(simulation_db.app_version())
    return ""


cfg = pkconfig.init(
    db_dir=pkconfig.ReplacedBy("sirepo.srdb.root"),
    enable_source_cache_key=(
        True,
        bool,
        "enable source cache key, disable to allow local file edits in Chrome",
    ),
    google_tag_manager_id=(None, str, "enable google analytics with this id"),
    home_page_uri=("/en/landing.html", str, "home page to redirect to"),
    react_server=(None, _cfg_react_server, "Base URL of npm start server"),
    react_sim_types=(("myapp", "jspec", "genesis"), set, "React apps"),
)
