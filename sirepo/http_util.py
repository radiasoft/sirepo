"""Support routines for http requests/responses

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog
import re
import sirepo.util

#: Http auth header name
_AUTH_HEADER = "Authorization"

#: http auth header scheme bearer
_AUTH_HEADER_SCHEME_BEARER = "Bearer"

#: Regex to test format of auth header and extract token
_AUTH_HEADER_RE = re.compile(
    _AUTH_HEADER_SCHEME_BEARER + r"\s+(" + sirepo.util.UNIQUE_KEY_CHARS_RE + ")",
    re.IGNORECASE,
)


def auth_header(token):
    """Construct RFC6750 auth header compatible with `requests`.

    Args:
      token (str): Secret to be included in the header
    Returns
      PKDict: auth header
    """
    return PKDict({_AUTH_HEADER: f"{_AUTH_HEADER_SCHEME_BEARER} {token}"})


def parse_auth_header(headers):
    """Parse and retrieve RFC6750 bearer token.

    Args:
      headers (object): Object containing a `get` method to retrieve headers by name.
    Returns:
      str: bearer token from header or None if invalid syntax
    """
    if not (h := headers.get(_AUTH_HEADER)):
        return None
    if m := _AUTH_HEADER_RE.search(h):
        return m.group(1)
    return None


def remote_ip(request):
    """IP address of client from request.

    Tornado covers 'X-Real-Ip' and 'X-Forwared-For'. This adds addition
    headers to check.

    Args:
      request (tornado.httputil.HTTPServerRequest): Incoming request
    Returns:
      str:  IP address of client

    """
    return request.headers.get("proxy-for", request.remote_ip)
