"""Requests hold context for API calls

:copyright: Copyright (c) 2019-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import contextlib
import dns.resolver
import dns.reversename
import pykern.quest
import sirepo.api_perm
import sirepo.flask
import sirepo.modules
import sirepo.uri
import sirepo.util
import re


_HTTP_DATA_ATTR = "http_data"

_PARENT_ATTR = "parent"

_SIM_TYPE_ATTR = "sim_type"

_SPEC_ATTR = "quest_spec"

_SPEC_SIM_TYPE_CONST = re.compile(r"\s*SimType\s+const=(\S+)")


@contextlib.contextmanager
def start(in_pkcli=False):
    auth = sirepo.modules.import_and_init("sirepo.auth")
    qcall = API(in_pkcli=in_pkcli)
    c = False
    try:
        auth.init_quest(qcall)
        yield qcall
        c = True
    finally:
        qcall.destroy(commit=c)


class API(pykern.quest.API):
    """Holds request context for all API calls."""

    def __init__(self, in_pkcli=False):
        super().__init__()
        self.attr_set("_bucket", _Bucket())
        self.bucket_set("in_pkcli", in_pkcli)

    def absolute_uri(self, uri):
        """Convert to an absolute uri

        Args:
            uri (str): must begin with "/"
        Returns:
            str: absolute uri
        """
        assert uri[0] == "/"
        return self.sreq.http_server_uri + uri[1:]

    def attr_set(self, name, obj):
        """Assign an object to qcall"""
        assert isinstance(obj, Attr)
        assert name not in self
        self[name] = obj

    def bucket_set(self, name, value):
        assert (
            name not in self._bucket
        ), f"duplicate name={name} in _bucket={list(self._bucket.keys())}"
        self._bucket[name] = value

    def bucket_unchecked_get(self, name):
        return self._bucket.get(name)

    async def call_api(self, name, kwargs=None, data=None):
        """Calls uri_router.call_api, which calls the API with permission checks.

        Args:
            name (object): api name (without `api_` prefix)
            kwargs (dict): to be passed to API [None]
            data (dict): will be returned `self.parse_json` [None]
        Returns:
            Reply: result
        """
        return await uri_router.call_api(self, name, kwargs=kwargs, data=data)

    def call_api_sync(self, *args, **kwargs):
        """Synchronous call_api

        Only use in tests.
        """
        import asyncio

        return asyncio.run(self.call_api(*args, **kwargs))

    def destroy(self, commit=False):
        for k, v in reversed(list(self.items())):
            if hasattr(v, "destroy") and not getattr(v, "quest_no_destroy", False):
                try:
                    v.destroy(commit=commit)
                except Exception:
                    pkdlog("destroy failed attr={} stack={}", v, pkdexc())
            self.pkdel(k)

    def headers_for_cache(self, resp, path=None):
        return resp.headers_for_cache(path)

    def headers_for_no_cache(self, resp):
        return resp.headers_for_no_cache()

    def http_data_set(self, data):
        self.bucket_set(_HTTP_DATA_ATTR, data)

    def http_data_uget(self):
        """Unchecked get for http_request.parse_post"""
        return self.bucket_unchecked_get(_HTTP_DATA_ATTR)

    def parent_set(self, qcall):
        assert isinstance(qcall, API)
        # must be right after initialization
        assert len(self._bucket.keys()) == 1
        assert len(self.keys()) == 1
        # TODO(robnagler): Consider nested transactions
        #
        # For now, we have to commit because we don't have nesting.
        # Commit at the end of this child-qcall which shares auth_db.
        # auth_db is robust here since it dynamically creates sessions.
        qcall.auth_db.commit()
        for k, v in qcall.items():
            if k not in ("uri_route", "_bucket", "sreply"):
                assert k not in self
                self[k] = v
        self._bucket[_PARENT_ATTR] = qcall
        self._bucket.in_pkcli = qcall.bucket_unchecked_get("in_pkcli")
        if "sreply" in qcall:
            qcall.sreply.init_child(self)

    def parse_json(self):
        return http_request.parse_json(self)

    def parse_params(self, **kwargs):
        return http_request.parse_post(
            self,
            PKDict(kwargs).pksetdefault(req_data=PKDict),
        )

    def parse_post(self, **kwargs):
        return http_request.parse_post(self, PKDict(kwargs))

    def reply(self, **kwargs):
        return self.sreply.from_kwargs(**kwargs)

    def reply_as_proxy(self, content, content_type):
        return self.sreply.from_kwargs(
            content=content,
            content_type=content_type,
        ).headers_for_no_cache()

    def reply_attachment(self, content_or_path, filename=None):
        return self.sreply.gen_attachment(
            content_or_path=content_or_path,
            filename=filename,
        )

    def reply_dict(self, value):
        return self.sreply.gen_dict(value)

    def reply_file(self, path, filename=None):
        return self.sreply.gen_file(path=path, filename=filename)

    def reply_html(self, path):
        return self.sreply.render_html(path)

    def reply_list_deprecated(self, value):
        """Always reply_dict, not with a list"""
        return self.sreply.gen_list_deprecated(value)

    def reply_ok(self, value=None):
        return self.sreply.gen_dict_ok(value)

    def reply_redirect(self, uri):
        return self.sreply.gen_redirect(uri)

    def reply_redirect_for_app_root(self, sim_type=None):
        return self.reply_redirect(self.uri_for_app_root(sim_type))

    def reply_redirect_for_local_route(
        self,
        sim_type=None,
        route=None,
        params=None,
        query=None,
        **kwargs,
    ):
        return self.sreply.gen_redirect_for_local_route(
            sim_type=sim_type,
            route=route,
            params=params,
            query=query,
            **kwargs,
        )

    def reply_static_jinja(self, base, ext, j2_ctx):
        return self.sreply.render_static_jinja(base, ext, j2_ctx)

    def sim_type_set(self, sim_type):
        """Set sim_type if there, else don't set"""
        if not sirepo.util.is_sim_type(sim_type):
            # Don't change sim_type unless we have a valid one
            return
        # Don't change once set
        if _SIM_TYPE_ATTR in self:
            return
        self._bucket[_SIM_TYPE_ATTR] = sim_type

    def sim_type_set_from_spec(self, func):
        s = getattr(func, _SPEC_ATTR).sim_type
        if s:
            self.sim_type_set(s)

    def sim_type_uget(self, value=None):
        """Return value or reuqest's sim_type

        Args:
            value (str): will be validated if not None
        Returns:
            str: sim_type or possibly None
        """
        if value:
            return sirepo.util.assert_sim_type(value)
        return self._bucket.get(_SIM_TYPE_ATTR)

    def uri_for_api(self, api_name, params=None):
        """Generate uri for api method

        Args:
            api_name (str): full name of api
            params (PKDict): paramters to pass to uri
        Returns:
            str: formmatted URI
        """
        return uri_router.uri_for_api(api_name=api_name, params=params)

    def uri_for_app_root(self, sim_type=None):
        """Return uri for sim_type

        Args:
            sim_type (str): sim_type (must be defined)
        Returns:
            str: uri
        """
        return sirepo.uri.app_root(sim_type=self.sim_type_uget(sim_type))

    def user_agent_headers(self):
        def _dns_reverse_lookup(ip):
            try:
                if ip:
                    return ", ".join(
                        [
                            str(i)
                            for i in dns.resolver.resolve(
                                dns.reversename.from_address(ip), "PTR"
                            ).rrset.items
                        ]
                    )
            # 127.0.0.1 is not reverse mapped, resulting in dns.resolver.NoNameservers exception
            except (
                dns.resolver.NoAnswer,
                dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers,
            ):
                pass
            return "No Reverse DNS Lookup"

        return PKDict(
            ip_addr=self.sreq.remote_addr,
            domain_name=_dns_reverse_lookup(self.sreq.remote_addr),
            user_agent=self.sreq.header_uget("User-Agent"),
        )


class Attr(PKDict):
    pass


class Spec(pykern.quest.Spec):
    def __init__(self, perm, **kwargs):
        self.perm = perm
        self.kwargs = PKDict(kwargs)
        self.sim_type = None
        m = _SPEC_SIM_TYPE_CONST.search(self.kwargs.get("sim_type") or "")
        self.sim_type = m.group(1) if m else None
        super().__init__()

    # TODO(robnagler) put this in super and just setattr perm.
    def __call__(self, func):
        def _wrapper(*args, **kwargs):
            return self.func(*args, **kwargs)

        self.func = func
        setattr(
            _wrapper,
            sirepo.api_perm.ATTR,
            getattr(sirepo.api_perm.APIPerm, self.perm.upper()),
        )
        setattr(_wrapper, _SPEC_ATTR, self)
        return _wrapper


class _Bucket(Attr):
    pass


def init_module(**imports):
    import sirepo.util

    # import http_request, uri_router, simulation_db
    sirepo.util.setattr_imports(imports)
