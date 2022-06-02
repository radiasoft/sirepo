u"""Replies for all API calls.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


class Base:
    @classmethod
    def exception(cls, exc):
        return http_reply.gen_exception(exc)

    @classmethod
    def file_as_attachment(cls, content_or_path, filename=None, content_type=None):
        return http_reply.gen_file_as_attachment(content_or_path, filename=filename, content_type=content_type)

    @classmethod
    def json(cls, value, pretty=False, response_kwargs=None):
        return http_reply.gen_json(value, pretty=pretty, response_kwargs=response_kwargs)

    @classmethod
    def json_ok(cls, *args, **kwargs):
        return http_reply.gen_json_ok(*args, **kwargs)

    @classmethod
    def redirect(cls, uri):
        return http_reply.gen_redirect(uri)

    @classmethod
    def redirect_for_anchor(cls, uri, **kwargs):
        return http_reply.gen_redirect_for_anchor(uri, **kwargs)

    @classmethod
    def redirect_for_app_root(cls, sim_type):
        return http_reply.gen_redirect_for_app_root(sim_type)

    @classmethod
    def redirect_for_local_route(cls, sim_type=None, route=None, params=None, query=None, **kwargs):
        return http_reply.gen_redirect_for_local_route(sim_type=sim_type, route=route, params=params, query=query, **kwargs)

    @classmethod
    def response(cls, *args, **kwargs):
        return http_reply.gen_response(*args, **kwargs)

    @classmethod
    def tornado_exception(cls, exc):
        return http_reply.gen_tornado_exception(exc)


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
