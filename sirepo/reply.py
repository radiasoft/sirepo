u"""Replies for all API calls.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


class Base:
    def gen_exception(self, exc):
        return http_reply.gen_exception(exc)

    def gen_file_as_attachment(self, content_or_path, filename=None, content_type=None):
        return http_reply.gen_file_as_attachment(content_or_path, filename=filename, content_type=content_type)

    def gen_json(self, value, pretty=False, response_kwargs=None):
        return http_reply.gen_json(value, pretty=pretty, response_kwargs=response_kwargs)

    def gen_json_ok(self, *args, **kwargs):
        return http_reply.gen_json_ok(*args, **kwargs)

    def gen_redirect(self, uri):
        return http_reply.gen_redirect(uri)

    def gen_redirect_for_anchor(self, uri, **kwargs):
        return http_reply.gen_redirect_for_anchor(uri, **kwargs)

    def gen_redirect_for_app_root(self, sim_type):
        return http_reply.gen_redirect_for_app_root(sim_type)

    def gen_redirect_for_local_route(self, sim_type=None, route=None, params=None, query=None, **kwargs):
        return http_reply.gen_redirect_for_local_route(sim_type=sim_type, route=route, params=params, query=query, **kwargs)

    def gen_response(self, *args, **kwargs):
        return http_reply.gen_response(*args, **kwargs)

    def gen_tornado_exception(self, exc):
        return http_reply.gen_tornado_exception(exc)


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
