"""Requests hold context for API calls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import flask


def begin():
    return _Base()


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)


class _Base:
    """Holds context for incoming requests"""

    # TODO(e-carlin): used to be named request_method
    def has_params(self):
        # TODO(e-carlin): naive and not accurate (ex. simulationFrame has params but is not a post)
        # but good enough for now
        return flask.request.method == "POST"

    @classmethod
    def headers(cls):
        return flask.request.headers
