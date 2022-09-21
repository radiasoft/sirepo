"""Requests hold context for API calls

:copyright: Copyright (c) 2019-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
import dns.resolver
import dns.reversename
import pykern.quest
import sirepo.api_perm
import sirepo.uri

class API(pykern.quest.API):
    """Holds request context for all API calls."""

    def absolute_uri(self, uri):
        """Convert to an absolute uri

        Args:
            uri (str): must begin with "/"
        Returns:
            str: absolute uri
        """
        assert uri[0] == "/"
        return self.sreq.server_uri + uri[1:]

    def create_sreq(self, **kwargs):
        import sirepo.request

        self.sreq = sirepo.request(

    def call_api(self, name, kwargs=None, data=None):
        """Calls uri_router.call_api, which calls the API with permission checks.

        Args:
            name (object): api name (without `api_` prefix)
            kwargs (dict): to be passed to API [None]
            data (dict): will be returned `self.parse_json` [None]
        Returns:
            flask.Response: result
        """
        return uri_router.call_api(self.sreq, name, kwargs=kwargs, data=data)

    def headers_for_no_cache(self, resp):
        return http_reply.headers_for_no_cache(resp)

    def parse_json(self):
        return http_request.parse_json(sapi)

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
            user_agent=self.sreq.http_header("User-Agent"),
        )


class Spec(pykern.quest.Spec):
    def __init__(self, perm, **kwargs):
        self.perm = perm
        self.kwargs = PKDict(kwargs)
        super().__init__()

    #TODO(robnagler) put this in super and just setattr perm.
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


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
