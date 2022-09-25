"""Requests hold context for API calls

:copyright: Copyright (c) 2019-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import dns.resolver
import dns.reversename
import pykern.quest
import sirepo.api_perm
import sirepo.uri
import sirepo.util


_HTTP_DATA_ATTR = "http_data"

_PARENT_ATTR = "parent"

_SIM_TYPE_ATTR = "sim_type"

_hack_current = None


def hack_current():
    if sirepo.util.in_flask_request():
        import flask

        return flask.g.get("sirepo_quest", None)
    else:
        global _hack_current

        return _hack_current


class API(pykern.quest.API):
    """Holds request context for all API calls."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attr_set("_bucket", _Bucket())
        if sirepo.util.in_flask_request():
            pkdp("in flask")
            import flask

            flask.g.sirepo_quest = self
        else:
            global _hack_current

            _hack_current = self

    # #TODO
    #     def handle_api_destroy(): called on the API
    #     call commit?
    #     implemented by the objects added
    #     order can be controlled eg auth, auth_db, cookie,

    #     need a save request, too.
    #     deferring to subrequests?

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
        assert name not in self._bucket
        self._bucket[name] = value

    def bucket_uget(self, name):
        return self._bucket.get(name)

    def call_api(self, name, kwargs=None, data=None):
        """Calls uri_router.call_api, which calls the API with permission checks.

        Args:
            name (object): api name (without `api_` prefix)
            kwargs (dict): to be passed to API [None]
            data (dict): will be returned `self.parse_json` [None]
        Returns:
            flask.Response: result
        """
        return uri_router.call_api(self, name, kwargs=kwargs, data=data)

    def destroy(self):
        if sirepo.util.in_flask_request():
            import flask

            flask.g.pop("sirepo_quest")
            flask.g.sirepo_quest = self.bucket_uget(_PARENT_ATTR)
        else:
            global _hack_current

            _hack_current = self.bucket_uget(_PARENT_ATTR)
        for k, v in reversed(list(self.items())):
            if hasattr(v, "destroy"):
                try:
                    v.destroy()
                except Exception:
                    pkdlog("destroy failed attr={} stack={}", v, pkdexc())
            self.pkdel(k)

    def headers_for_no_cache(self, resp):
        return http_reply.headers_for_no_cache(resp)

    def http_data_set(self, data):
        self.bucket_set(_HTTP_DATA_ATTR, data)

    def http_data_uget(self):
        """Unchecked get for http_request.parse_post"""
        return self.bucket_uget(_HTTP_DATA_ATTR)

    def parent_set(self, qcall):
        pkdp(qcall)
        pkdp(type(qcall))
        assert isinstance(qcall, API)
        # must be right after initialization
        assert not self._bucket
        assert len(self.keys()) == 1
        for k, v in qcall.items():
            if k not in ("uri_route", "_bucket"):
                assert k not in self
                self[k] = v
        self._bucket[_PARENT_ATTR] = qcall

    def parse_json(self):
        return http_request.parse_json(self)

    def parse_params(self, **kwargs):
        return http_request.parse_post(
            self,
            PKDict(kwargs).pksetdefault(req_data=PKDict),
        )

    def parse_post(self, **kwargs):
        return http_request.parse_post(self, PKDict(kwargs))

    def reply(self, *args, **kwargs):
        return http_reply.gen_response(*args, **kwargs)

    def reply_as_proxy(self, response):
        r = http_reply.gen_response(response.content)
        # TODO(robnagler) requests seems to return content-encoding gzip, but
        # it doesn't seem to be coming from npm
        r.headers["Content-Type"] = response.headers["Content-Type"]
        return http_reply.headers_for_no_cache(r)

    def reply_attachment(self, content_or_path, filename=None, content_type=None):
        return http_reply.gen_file_as_attachment(
            self, content_or_path, filename=filename, content_type=content_type
        )

    def reply_file(self, path, content_type=None):
        import flask

        return flask.send_file(str(path), mimetype=content_type, conditional=True)

    def reply_html(self, path):
        return http_reply.render_html(path)

    def reply_json(self, value, pretty=False, response_kwargs=None):
        return http_reply.gen_json(
            value, pretty=pretty, response_kwargs=response_kwargs
        )

    def reply_ok(self, *args, **kwargs):
        return http_reply.gen_json_ok(*args, **kwargs)

    def reply_redirect(self, uri):
        return http_reply.gen_redirect(uri)

    def reply_redirect_for_local_route(
        self,
        sim_type=None,
        route=None,
        params=None,
        query=None,
        **kwargs,
    ):
        return http_reply.gen_redirect_for_local_route(
            self.sreq,
            sim_type=sim_type,
            route=route,
            params=params,
            query=query,
            **kwargs,
        )

    def reply_static_jinja(self, base, ext, j2_ctx, cache_ok=False):
        return http_reply.render_static_jinja(base, ext, j2_ctx, cache_ok=cache_ok)

    def sim_type_set(self, sim_type):
        """Set sim_type if there, else don't set"""
        if not sirepo.util.is_sim_type(sim_type):
            # Don't change sim_type unless we have a valid one
            return
        # Don't change once set
        if _SIM_TYPE_ATTR in self:
            return
        self._bucket[_SIM_TYPE_ATTR] = sim_type

    def sim_type_uget(self, value=None):
        """Return value or reuqest's sim_type

        Args:
            value (str): will be validated if not None
        Returns:
            str: sim_type or possibly None
        """
        if value:
            return sirepo.util.assert_sim_type(value)
        t = self._bucket.get(_SIM_TYPE_ATTR)

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
        return sirepo.uri.app_root(self, sim_type=sim_type)

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
            user_agent=self.http_header_uget("User-Agent"),
        )


class Attr(PKDict):
    pass


class Spec(pykern.quest.Spec):
    def __init__(self, perm, **kwargs):
        self.perm = perm
        self.kwargs = PKDict(kwargs)
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
        return _wrapper


class _Bucket(Attr):
    pass


def init_module(**imports):
    import sirepo.util

    # import http_reply, http_request, uri_router, simulation_db
    sirepo.util.setattr_imports(imports)
