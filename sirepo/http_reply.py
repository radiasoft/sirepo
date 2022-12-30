# -*- coding: utf-8 -*-
"""response generation

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkconst
from pykern import pkio
from pykern import pkjinja
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import mimetypes
import pykern.pkinspect
import re
import sirepo.html
import sirepo.http_request
import sirepo.resource
import sirepo.uri
import sirepo.util


#: data.state for srException
SR_EXCEPTION_STATE = "srException"

#: mapping of extension (json, js, html) to MIME type
MIME_TYPE = None

#: default Max-Age header
CACHE_MAX_AGE = 43200

_ERROR_STATE = "error"

_STATE = "state"

#: Default response
_RESPONSE_OK = PKDict({_STATE: "ok"})

#: Parsing errors from subprocess
_SUBPROCESS_ERROR_RE = re.compile(
    r"(?:warning|exception|error): ([^\n]+?)(?:;|\n|$)", flags=re.IGNORECASE
)

#: routes that will require a reload
_RELOAD_JS_ROUTES = None
