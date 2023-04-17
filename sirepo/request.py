# -*- coding: utf-8 -*-
"""Requests hold context for API calls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import base64
import email.utils
import pykern.pkcompat
import sirepo.const
import sirepo.quest
import sirepo.util
import urllib.parse
import user_agents


_POST_ATTR = "sirepo_http_request_post"

_SIM_TYPE_ATTR = "sirepo_http_request_sim_type"

#: We always use the same name for a file upload
_FORM_FILE_NAME = "file"


def init_quest(qcall, internal_req=None):
    if qcall.bucket_unchecked_get("in_pkcli"):
        sreq = _SRequest(
            http_authorization=None,
            http_headers=PKDict(),
            http_method="GET",
            http_request_uri="/",
            http_server_uri="http://localhost/",
            internal_req=internal_req,
            remote_addr="0.0.0.0",
        )
    elif "werkzeug" in str(type(internal_req)):
        import flask

        sreq = _SRequest(
            body_as_bytes=lambda: internal_req.get_data(cache=False),
            http_authorization=internal_req.authorization,
            http_headers=internal_req.headers,
            http_method=internal_req.method,
            http_request_uri=internal_req.url,
            http_server_uri=flask.url_for("_flask_dispatch_empty", _external=True),
            internal_req=internal_req,
            remote_addr=internal_req.remote_addr,
            _form_file_class=_FormFileFlask,
            _form_get=internal_req.form.get,
        )
    elif "tornado" in str(type(internal_req)):
        r = internal_req.request
        u = f"{r.protocol}://{r.host}"
        sreq = _SRequest(
            body_as_bytes=lambda: internal_req.request.body,
            http_authorization=_parse_authorization(r.headers.get("Authorization")),
            http_headers=r.headers,
            http_method=r.method,
            http_request_uri=u + r.path,
            http_server_uri=u + "/",
            internal_req=internal_req,
            remote_addr=r.remote_ip,
            _form_file_class=_FormFileTornado,
            _form_get=internal_req.get_argument,
        )
    else:
        raise AssertionError(f"unknown internal_req={type(internal_req)}")
    qcall.attr_set("sreq", sreq)


def _parse_authorization(value):
    if not value:
        return None
    try:
        t, i = value.split(None, 1)
        t = t.lower()
    except Exception:
        raise sirepo.util.Forbidden("unparseable authorization header={}", value)
    if t != "basic":
        raise sirepo.util.Forbidden("unhandled authorization type={}", t)
    try:
        u, p = base64.b64decode(i).split(b":", 1)
    except Exception:
        raise sirepo.util.Forbidden("unparseable authorization info={} type={}", i, t)
    return PKDict(
        type=t,
        username=pykern.pkcompat.from_bytes(u),
        password=pykern.pkcompat.from_bytes(p),
    )


class _FormFileBase(PKDict):
    def __init__(self, sreq):
        super().__init__()
        f = self._get(sreq.internal_req)
        if not f:
            raise sirepo.util.Error("must supply a file", "no file in request={}", sreq)
        self.filename = f.filename
        self._internal = f

    def as_str(self):
        return pykern.pkcompat.from_bytes(self.as_bytes())


class _FormFileFlask(_FormFileBase):
    def as_bytes(self):
        return self._internal.stream.read()

    def _get(self, internal_req):
        return internal_req.files.get(_FORM_FILE_NAME)


class _FormFileTornado(_FormFileBase):
    def as_bytes(self):
        # TODO(robnagler) need to garbage collect
        return self._internal.body

    def _get(self, internal_req):
        res = internal_req.request.files.get(_FORM_FILE_NAME)
        if not res:
            return None
        if len(res) > 1:
            raise sirepo.util.BadRequest("too many files={} in form", len(res))
        return res[0]


class _SRequest(sirepo.quest.Attr):
    """Holds context for incoming requests"""

    def content_type_eq(self, value):
        c = self.__content_type()._key
        if c is None:
            return False
        return self.__content_type()._key.lower() == value.lower()

    def form_get(self, name, default):
        return self._form_get(name, default)

    def form_file_get(self):
        return self._form_file_class(self)

    def header_uget(self, key):
        return self.http_headers.get(key)

    def is_spider(self):
        a = self.header_uget("User-Agent")
        if not a:
            # assume it's a spider if there's no header
            return True
        if a.startswith(sirepo.const.SRUNIT_USER_AGENT):
            # So our unit tests can run
            return False
        if "python-requests" in a:
            # user_agents doesn't see Python's requests module as a bot.
            # The package robot_detection does see it, but we don't want to introduce another dependency.
            return True
        return user_agents.parse(a).is_bot

    def method_is_post(self):
        return self.http_method == "POST"

    def set_post(self, data=None):
        """Interface for uri_router"""
        # Always remove data (if there)
        res = self.get(_POST_ATTR)
        if data is not None:
            self[_POST_ATTR] = data
        return res

    def __content_type(self):
        if "_content_type" not in self:
            self._content_type = self._parse_header(
                self.header_uget("Content-Type") or ""
            )
        return self._content_type

    def _parse_header(self, line):
        r"""Parse a Content-type like header.

        Copied from tornado.httputil._parse_header

        Return the main content-type and a dictionary of options.

        >>> d = "form-data; foo=\"b\\\\a\\\"r\"; file*=utf-8''T%C3%A4st"
        >>> ct, d = _parse_header(d)
        >>> ct
        'form-data'
        >>> d['file'] == r'T\u00e4st'.encode('ascii').decode('unicode_escape')
        True
        >>> d['foo']
        'b\\a"r'
        """

        def _parseparam(s):
            # tornado.httputil._parseparam
            while s[:1] == ";":
                s = s[1:]
                end = s.find(";")
                while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
                    end = s.find(";", end + 1)
                if end < 0:
                    end = len(s)
                f = s[:end]
                yield f.strip()
                s = s[end:]

        parts = _parseparam(";" + line)
        key = next(parts)
        if len(key) == 0:
            return PKDict(_key=None)
        # decode_params treats first argument special, but we already stripped key
        params = [("Dummy", "value")]
        for p in parts:
            i = p.find("=")
            if i >= 0:
                name = p[:i].strip().lower()
                value = p[i + 1 :].strip()
                params.append((name, value))
        decoded_params = email.utils.decode_params(params)
        decoded_params.pop(0)  # get rid of the dummy again
        pdict = {}
        for name, decoded_value in decoded_params:
            value = email.utils.collapse_rfc2231_value(decoded_value)
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            pdict[name] = value
        return PKDict(pdict, _key=key)
