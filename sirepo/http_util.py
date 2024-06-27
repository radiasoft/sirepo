"""Support routines for http requests/responses

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog
import re
import sirepo.job

#: Http auth header name
_AUTH_HEADER = "Authorization"

#: http auth header scheme bearer
_AUTH_HEADER_SCHEME_BEARER = "Bearer"

#: Regex to test format of auth header and extract token
_AUTH_HEADER_RE = re.compile(
    _AUTH_HEADER_SCHEME_BEARER + r"\s(" + sirepo.job.UNIQUE_KEY_CHARS_RE + ")",
    re.IGNORECASE,
)


def auth_header(token):
    """Construct auth header object.

    Args:
      token (str): Secret to be included in the header
    Returns
      PKDict: auth header
    """
    return PKDict({_AUTH_HEADER: f"{_AUTH_HEADER_SCHEME_BEARER} {token}"})


def parse_auth_header(headers):
    """Validate and retrieve authentication header.

    Args:
      headers (object): Object containing a `get` method to retrieve headers by name.
    Returns:
      bool|str: False if parseable auth header not found otherwise token from auth header.
    """
    if not (h := headers.get(_AUTH_HEADER)):
        return False
    if m := _AUTH_HEADER_RE.search(h):
        return m.group(1)
    return False
