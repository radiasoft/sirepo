u"""Requests hold context for API calls

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


class Base:
    """Holds request context for all API calls.
    """

    def call_api(self, name, kwargs=None, data=None):
        """Calls uri_router.call_api, which calls the API with permission checks.

        Args:
            name (object): api name (without `api_` prefix)
            kwargs (dict): to be passed to API [None]
            data (dict): will be returned `self.parse_json` [None]
        Returns:
            flask.Response: result
        """
        return uri_router.call_api(name, kwargs=kwargs, data=data)

    def parse_json(self):
        return http_request.parse_json()

    def parse_params(self, **kwargs):
        return http_request.parse_params(**kwargs)

    def parse_post(self, **kwargs):
        return http_request.parse_post(**kwargs)

    def reply_file(self, content_or_path, filename=None, content_type=None):
        return http_reply.gen_file_as_attachment(content_or_path, filename=filename, content_type=content_type)

    def reply_json(self, value, pretty=False, response_kwargs=None):
        return http_reply.gen_json(value, pretty=pretty, response_kwargs=response_kwargs)

    def reply_ok(self, *args, **kwargs):
        return http_reply.gen_json_ok(*args, **kwargs)

    def reply_redirect(self, uri):
        return http_reply.gen_redirect(uri)

    def reply_redirect_for_app_root(self, sim_type):
        return http_reply.gen_redirect_for_app_root(sim_type)

    def reply_redirect_for_local_route(self, sim_type=None, route=None, params=None, query=None, **kwargs):
        return http_reply.gen_redirect_for_local_route(sim_type=sim_type, route=route, params=params, query=query, **kwargs)


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
