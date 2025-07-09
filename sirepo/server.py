# -*- coding: utf-8 -*-
"""Primary sirepo.quest.API's

:copyright: Copyright (c) 2015-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import simulation_db
import datetime
import re
import sirepo.const
import sirepo.feature_config
import sirepo.quest
import sirepo.resource
import sirepo.sim_data
import sirepo.sim_run
import sirepo.srschema
import sirepo.srtime
import sirepo.uri
import sirepo.util
import urllib.parse


# TODO(pjm): this import is required to work-around template loading in listSimulations, see #1151
if any(
    k in sirepo.feature_config.cfg().sim_types
    for k in ("flash", "radia", "silas", "warppba", "warpvnd")
):
    import h5py


#: See `_proxy_vue`
_PROXY_VUE_URI_RE = None

#: See `_proxy_vue`
_VUE_SERVER_BUILD = "build"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_plan", sid="SimId")
    async def api_copyNonSessionSimulation(self):
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
        return self._save_with_related(req, data)

    @sirepo.quest.Spec(
        "require_plan",
        sid="SimId",
        folder="SimFolderName",
        name="SimName",
    )
    async def api_copySimulation(self):
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

    @sirepo.quest.Spec("require_plan", filename="SimFileName", file_type="SimFileType")
    async def api_deleteFile(self):
        """Deprecated - use `api_deleteLibFile`"""
        return await self.api_deleteLibFile()

    @sirepo.quest.Spec("require_plan", filename="SimFileName", file_type="SimFileType")
    async def api_deleteLibFile(self):
        req = self.parse_post(filename=True, file_type=True)
        e = _simulations_using_file(req)
        if len(e):
            return self.reply_dict(
                {
                    "error": "File is in use in other simulations.",
                    "fileList": e,
                    "fileName": req.filename,
                }
            )

        # Will not remove resource (standard) lib files, because those
        # live in the resource directoy.
        pkio.unchecked_remove(_lib_file_write_path(req))
        return self.reply_ok()

    @sirepo.quest.Spec("require_plan", sid="SimId")
    async def api_deleteSimulation(self):
        req = self.parse_post(id=True)
        simulation_db.delete_simulation(req.type, req.id, qcall=self)
        return self.reply_ok()

    @sirepo.quest.Spec("require_plan", filename="SimFileName")
    async def api_downloadFile(self, simulation_type, simulation_id, filename):
        """Deprecated - use `api_downloadLibFile`"""
        return await self.api_downloadLibFile(simulation_type, filename)

    @sirepo.quest.Spec("require_plan", filename="SimFileName")
    async def api_downloadLibFile(self, simulation_type, filename):
        req = self.parse_params(type=simulation_type, filename=filename)
        return self.reply_attachment(
            req.sim_data.lib_file_abspath(req.filename, qcall=self),
            filename=req.sim_data.lib_file_name_without_type(req.filename),
        )

    @sirepo.quest.Spec("allow_visitor", spec="ErrorLoggingSpec")
    async def api_errorLogging(self):
        ip = self.sreq.remote_addr
        try:
            pkdlog(
                "{}: javascript error: {}",
                ip,
                simulation_db.generate_json(self.body_as_dict(), pretty=True),
            )
        except Exception as e:
            try:
                b = self.sreq.body_as_bytes().decode("unicode-escape")
            except Exception as e:
                b = f"error={e}"
            pkdlog("ip={}: error parsing javascript exception={} input={}", ip, e, b)
        return self.reply_ok()

    @sirepo.quest.Spec(
        "require_user", simulation_id="SimId", filename="SimExportFileName"
    )
    async def api_exportArchive(self, simulation_type, simulation_id, filename):
        req = self.parse_params(
            template=True,
            filename=filename,
            id=simulation_id,
            type=simulation_type,
        )
        from sirepo import exporter

        return exporter.create_archive(req, self)

    @sirepo.quest.Spec("allow_visitor")
    async def api_favicon(self):
        """Routes to favicon.ico file."""
        # SECURITY: We control the path of the file so using send_file is ok.
        return self.reply_file(sirepo.resource.static("img", "favicon.ico"))

    @sirepo.quest.Spec("allow_visitor")
    async def api_faviconPng(self):
        """Routes to favicon.png file."""
        # SECURITY: We control the path of the file so using send_file is ok.
        return self.reply_file(sirepo.resource.static("img", "favicon.png"))

    @sirepo.quest.Spec("allow_visitor")
    async def api_forbidden(self):
        raise sirepo.util.Forbidden("app forced forbidden")

    @sirepo.quest.Spec(
        "require_plan",
        file_type="LibFileType",
    )
    async def api_listFiles(self):
        req = self.parse_post(file_type=True)
        return self.reply_list_deprecated(
            req.sim_data.lib_file_names_for_type(req.file_type, qcall=self),
        )

    @sirepo.quest.Spec(
        "allow_visitor", application_mode="AppMode", simulation_name="SimName"
    )
    async def api_findByName(self, simulation_type, application_mode, simulation_name):
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
        "require_plan",
        application_mode="AppMode",
        simulation_name="SimName",
    )
    async def api_findByNameWithAuth(
        self, simulation_type, application_mode, simulation_name
    ):
        """Find `simulation_name` in library

        POSIT: sirepo.status assumes this returns a redirect
        """
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
                raise sirepo.util.NotFound(
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
        "require_plan",
        file="ImportFile",
        folder="SimFolderPath",
        sid="SimId",
        arguments="ImportArgs optional",
    )
    async def api_importFile(self, simulation_type):
        """
        Args:
            simulation_type (str): which simulation type
        Params:
            file: file data
            folder: where to import to
        """
        from sirepo import importer

        def _save_sim(req, data):
            data.models.simulation.folder = req.folder
            data.models.simulation.isExample = False
            return self._save_new_and_reply(req, data)

        async def _stateful_compute(req):
            r = await self.call_api(
                "statefulCompute",
                body=PKDict(
                    method="import_file",
                    args=req.sim_data.prepare_import_file_args(req=req),
                    simulationType=req.type,
                ),
            )
            try:
                res = r.content_as_object().imported_data
                r.destroy()
                return res
            except Exception:
                raise sirepo.util.SReplyExc(r)

        error = None
        f = None
        try:
            f = self.sreq.form_file_get()
            req = self.parse_params(
                filename=f.filename,
                folder=self.sreq.form_get("folder", None),
                id=self.sreq.form_get("simulationId", None),
                template=True,
                type=simulation_type,
            )
            req.form_file = f
            req.import_file_arguments = self.sreq.form_get("arguments", "")
            if pkio.has_file_extension(req.filename, "json"):
                data = importer.read_json(req.form_file.as_bytes(), self, req.type)
            elif pkio.has_file_extension(req.filename, "zip"):
                data = await importer.read_zip(
                    req.form_file.as_bytes(), self, sim_type=req.type
                )
            elif hasattr(req.template, "stateful_compute_import_file"):
                data = await _stateful_compute(req)
            else:
                raise sirepo.util.Error(
                    "Only zip files are supported",
                    "no stateful_compute_import_file req={}",
                    req,
                )
            if "error" in data:
                return self.reply_dict(data)
            return _save_sim(req, data)
        except sirepo.util.ReplyExc:
            raise
        except Exception as e:
            pkdlog("{}: exception: {}", f and f.filename, pkdexc())
            # TODO(robnagler) security issue here. Really don't want to report all errors to user
            if hasattr(e, "args"):
                if len(e.args) == 1:
                    error = str(e.args[0])
                else:
                    error = str(e.args)
            else:
                error = str(e)
        return self.reply_dict(PKDict(error=error or "An unknown error occurred"))

    @sirepo.quest.Spec("allow_visitor", path_info="PathInfo optional")
    async def api_homePage(self, path_info=None):
        return await self.call_api(
            "staticFile", kwargs=PKDict(path_info="en/" + (path_info or "landing.html"))
        )

    @sirepo.quest.Spec("require_plan", folder="FolderName", name="SimName")
    async def api_newSimulation(self):
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
    async def api_notFound(self, *args, **kwargs):
        raise sirepo.util.NotFound("app forced not found (uri parsing error)")

    @sirepo.quest.Spec(
        "require_user",
        simulation_id="SimId",
        model="ComputeModelName optional",
        title="DownloadNamePostfix optional",
    )
    async def api_pythonSource(
        self, simulation_type, simulation_id, model=None, title=None
    ):
        req = self.parse_params(type=simulation_type, id=simulation_id, template=True)
        m = model and req.sim_data.parse_model(model)
        d = simulation_db.read_simulation_json(req.type, sid=req.id, qcall=self)
        suffix = simulation_db.get_schema(
            simulation_type
        ).constants.simulationSourceExtension
        return self.reply_attachment(
            req.template.python_source_for_model(d, model=m, qcall=self),
            filename="{}.{}".format(
                d.models.simulation.name + ("-" + title if title else ""),
                "madx" if m == "madx" else suffix,
            ),
        )

    @sirepo.quest.Spec("allow_visitor")
    async def api_robotsTxt(self):
        """Disallow the app (dev, prod) or / (alpha, beta)"""
        # We include dev so we can test
        if pkconfig.channel_in("prod", "dev"):
            u = [
                self.uri_for_app_root(x)
                for x in sorted(sirepo.feature_config.cfg().sim_types)
            ]
        else:
            u = ["/"]
        return self.reply(
            content="".join(
                ["User-agent: *\n"] + ["Disallow: {}\n".format(x) for x in u],
            ),
            content_type="text/plain",
        )

    @sirepo.quest.Spec("allow_visitor", path_info="PathInfo")
    async def api_root(self, path_info=None):
        from sirepo import template

        self._proxy_vue(path_info)
        if path_info is None:
            return self.reply_redirect(_cfg.home_page_uri)
        if template.is_sim_type(path_info):
            return self._render_root_page("index", PKDict(app_name=path_info))
        u = sirepo.uri.unchecked_root_redirect(path_info)
        if u:
            return self.reply_redirect(u)
        raise sirepo.util.NotFound(f"unknown path={path_info}")

    @sirepo.quest.Spec("require_plan", sid="SimId", data="SimData all_input")
    async def api_saveSimulationData(self):
        # do not fixup_old_data yet
        req = self.parse_post(id=True, template=True)
        return self._simulation_data_reply(
            req,
            simulation_db.save_simulation_json(
                req.req_data, fixup=True, modified=True, qcall=self
            ),
        )

    @sirepo.quest.Spec("allow_visitor")
    async def api_securityTxt(self):
        d = sirepo.srtime.utc_now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + datetime.timedelta(days=365)
        return self.reply(
            content="".join(
                [
                    f"Contact: mailto:{sirepo.feature_config.cfg().schema_common.support_email}\n",
                    f"Expires: {d.isoformat()}Z\n",
                ]
            ),
            content_type="text/plain",
        )

    @sirepo.quest.Spec(
        "require_plan",
        simulation_id="SimId",
        pretty="Bool optional",
        section="Section",
    )
    async def api_simulationData(
        self, simulation_type, simulation_id, pretty=False, section=None
    ):
        """First entry point for a simulation

        Might be non-session simulation copy (see `simulation_db.CopyRedirect`).
        We have to allow a non-user to get data.
        """

        def _not_found(req):
            if not simulation_db.find_global_simulation(req.type, req.id):
                raise sirepo.util.NotFound(
                    "sim_type={} sid={} global simulation not found", req.type, req.id
                )
            return self.headers_for_no_cache(self.reply_dict(_redirect(req)))

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
    async def api_listSimulations(self):
        req = self.parse_post()
        return self.reply_list_deprecated(
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

    @sirepo.quest.Spec("require_plan")
    async def api_simulationRedirect(self, simulation_type, local_route, simulation_id):
        return self.reply_redirect_for_local_route(
            sim_type=simulation_type,
            route=local_route,
            params=PKDict(simulationId=simulation_id),
        )

    # visitor rather than user because error pages are rendered by the application
    @sirepo.quest.Spec("allow_visitor")
    async def api_simulationSchema(self):
        if not (t := self.sreq.form_get("simulationType", "")):
            raise sirepo.util.NotFound("missing simulationType")
        req = self.parse_params(type=t)
        if self.auth.is_logged_in():
            simulation_db.simulation_dir(req.type, qcall=self)
        return self.reply_dict(simulation_db.get_schema(req.type))

    @sirepo.quest.Spec("allow_visitor")
    async def api_srwLight(self):
        return self._render_root_page("light", PKDict())

    @sirepo.quest.Spec("allow_visitor", path_info="FilePath")
    async def api_staticFile(self, path_info=None):
        """Send file from static folder.

        Args:
            path_info (str): relative path to join
        Returns:
            Reply: reply with file
        """
        if not path_info:
            raise sirepo.util.NotFound("empty path info")
        self._proxy_vue(f"{sirepo.const.STATIC_D}/" + path_info)
        p = sirepo.resource.static(sirepo.util.validate_path(path_info))
        if re.match(r"^(html|en)/[^/]+html$", path_info):
            return self.reply_html(p)
        return self.reply_file(p)

    @sirepo.quest.Spec("require_plan", oldName="SimFolderPath", newName="SimFolderPath")
    async def api_updateFolder(self):
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
        with simulation_db.user_lock(qcall=self):
            for r in simulation_db.iterate_simulation_datafiles(
                req.type,
                _simulation_data_iterator,
                qcall=self,
            ):
                f = r.models.simulation.folder
                if f.lower() == o.lower():
                    r.models.simulation.folder = n
                elif f.lower().startswith(o.lower() + "/"):
                    r.models.simulation.folder = n + f[len() :]
                else:
                    continue
                simulation_db.save_simulation_json(r, fixup=False, qcall=self)
        return self.reply_ok()

    @sirepo.quest.Spec(
        "require_plan",
        file="LibFile",
        file_type="LibFileType",
        simulation_id="SimId",
        confirm="Bool optional",
    )
    async def api_uploadFile(self, simulation_type, simulation_id, file_type):
        """Deprecated - use `api_uploadLibFile`"""
        return await self.api_uploadLibFile(simulation_type, simulation_id, file_type)

    @sirepo.quest.Spec(
        "require_plan",
        file="LibFile",
        file_type="LibFileType",
        simulation_id="SimId",
        confirm="Bool optional",
    )
    async def api_uploadLibFile(self, simulation_type, simulation_id, file_type):
        f = self.sreq.form_file_get()
        req = self.parse_params(
            file_type=file_type,
            filename=f.filename,
            id=simulation_id,
            template=True,
            type=simulation_type,
        )
        e = None
        in_use = None
        with sirepo.sim_run.tmp_dir(qcall=self) as d:
            t = d.join(req.filename)
            t.write_binary(f.as_bytes())
            if hasattr(req.template, "validate_file"):
                # Note: validate_file may modify the file
                e = req.template.validate_file(req.file_type, t)
            if (
                not e
                and req.sim_data.lib_file_exists(req.filename, qcall=self)
                and not self.sreq.form_get("confirm", False)
            ):
                in_use = _simulations_using_file(req, ignore_sim_id=req.id)
                if in_use:
                    e = "File is in use in other simulations. Please confirm you would like to replace the file for all simulations."
            if e:
                return self.reply_dict(
                    {
                        "error": e,
                        "filename": req.filename,
                        "fileList": in_use,
                        "fileType": req.file_type,
                        "simulationId": req.id,
                    }
                )
            t.rename(_lib_file_write_path(req))
        return self.reply_dict(
            {
                "filename": req.filename,
                "fileType": req.file_type,
                "simulationId": req.id,
            }
        )

    def _proxy_vue(self, path):
        import requests

        def _build():
            p = path
            m = re.search(r"^(\w+)(?:$|/)", p)
            if m and m.group(1) in sirepo.feature_config.cfg().sim_types:
                p = "index.html"
            # do not call api_staticFile due to recursion of _proxy_vue()
            r = self.reply_file(
                sirepo.resource.static(sirepo.util.validate_path(f"vue/{p}")),
            )
            if p == "index.html":
                # Ensures latest vue is always returned, because index.html contains
                # version-tagged values but index.html does not. It's likely that
                # a check would be made on a refresh, this ensures no caching.
                r.headers_for_no_cache()
            raise sirepo.util.SReplyExc(r)

        def _dev():
            p = path
            m = re.search(r"(\?.*)", self.sreq.http_request_uri)
            if m:
                p += m.group(1)
            r = requests.get(_cfg.vue_server + p)
            # We want to throw an exception here, because it shouldn't happen
            r.raise_for_status()
            raise sirepo.util.SReplyExc(
                self.reply_as_proxy(
                    content=r.content,
                    content_type=r.headers["Content-Type"],
                ),
            )

        if path and _cfg.vue_server and _PROXY_VUE_URI_RE.search(path):
            _build() if _cfg.vue_server == _VUE_SERVER_BUILD else _dev()

    def _render_root_page(self, page, values):
        values.update(
            PKDict(
                app_version=simulation_db.app_version(),
                source_cache_key=_source_cache_key(),
                static_files=simulation_db.static_libs(),
            )
        )
        return self.reply_static_jinja(page, "html", values)

    def _save_new_and_reply(self, req, data):
        return self._simulation_data_reply(
            req,
            simulation_db.save_new_simulation(data, qcall=self),
        )

    def _save_with_related(self, req, data):
        if hasattr(req.template, "copy_related_sims"):
            return self._save_new_and_reply(
                req,
                req.template.copy_related_sims(data, qcall=self),
            )
        return self._save_new_and_reply(req, data)

    def _simulation_data_reply(self, req, data):
        if hasattr(req.template, "prepare_for_client"):
            d = req.template.prepare_for_client(data, qcall=self)
        return self.headers_for_no_cache(self.reply_dict(data))


def init_apis(*args, **kwargs):
    pass


def init_tornado(use_reloader=False, is_server=False):
    """Initialize globals and create/upgrade db"""
    _init_proxy_vue()
    from sirepo import auth_db

    with sirepo.quest.start() as qcall:
        qcall.auth_db.create_or_upgrade()


def init_module(**imports):
    pass


def _cfg_vue_server(value):
    if value is None:
        return None
    if value == _VUE_SERVER_BUILD:
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


def _init_proxy_vue():
    if not _cfg.vue_server:
        return
    global _PROXY_VUE_URI_RE
    r = (
        r"^(assets)"
        if _cfg.vue_server == _VUE_SERVER_BUILD
        else r"^(@|src/|node_modules/)"
    )
    for x in sirepo.feature_config.cfg().vue_sim_types:
        r += rf"|^{x}(?:\/|$)"
    _PROXY_VUE_URI_RE = re.compile(r)


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
    if _cfg.enable_source_cache_key:
        return "?{}".format(simulation_db.app_version())
    return ""


_cfg = pkconfig.init(
    db_dir=pkconfig.ReplacedBy("sirepo.srdb.root"),
    enable_source_cache_key=(
        True,
        bool,
        "enable source cache key, disable to allow local file edits in Chrome",
    ),
    home_page_uri=("/en/landing.html", str, "home page to redirect to"),
    vue_server=(
        None if pkconfig.in_dev_mode() else _VUE_SERVER_BUILD,
        _cfg_vue_server,
        f"Base URL of npm start server or '{_VUE_SERVER_BUILD}'",
    ),
)
