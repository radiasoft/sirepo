u"""Requests hold context for API calls

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


class Base:
    """Holds request context for all API calls.
    """

    def __init__(self):
        self.reply = reply.Base()

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

def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
