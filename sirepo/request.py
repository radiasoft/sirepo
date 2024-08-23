"""Requests hold context for API calls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc
import base64
import email.utils
import pykern.pkcompat
import pykern.pkjson
import sirepo.const
import sirepo.http_util
import sirepo.quest
import sirepo.util
import user_agents


#: We always use the same name for a file upload
_FORM_FILE_NAME = "file"


def init_quest(qcall, internal_req=None):
    def _class():
        if qcall.bucket_unchecked_get("in_pkcli"):
            return _SRequestCLI
        elif "websocket" in str(type(internal_req)).lower():
            return _SRequestWebSocket
        elif "tornado" in str(type(internal_req)):
            return _SRequestHTTP
        else:
            raise AssertionError(f"unknown internal_req={type(internal_req)}")

    _class().init_quest(qcall, internal_req=internal_req)


class _FormFileBase(PKDict):
    def __init__(self, sreq):
        super().__init__()
        f = self._get(sreq.internal_req)
        if not f:
            raise sirepo.util.Error("must supply a file", "no file in request={}", sreq)
        self.filename = f.filename
        # TODO(robnagler) need to garbage collect
        self._internal = f

    def as_str(self):
        return pykern.pkcompat.from_bytes(self.as_bytes())


class _FormFileHTTP(_FormFileBase):
    def as_bytes(self):
        return self._internal.body

    def _get(self, internal_req):
        res = internal_req.request.files.get(_FORM_FILE_NAME)
        if not res:
            return None
        if len(res) > 1:
            raise sirepo.util.BadRequest("too many files={} in form", len(res))
        return res[0]


class _FormFileWebSocket(_FormFileBase):
    def as_bytes(self):
        return self._internal.blob

    def _get(self, internal_req):
        return internal_req.get("attachment")


class _SRequestBase(sirepo.quest.Attr):
    """Holds context for incoming requests"""

    # bare minimum to operate a child quest
    _INIT_QUEST_FOR_CHILD_KEYS = frozenset(
        (
            "http_authorization",
            "http_headers",
            "http_method",
            "http_server_uri",
            "remote_addr",
        )
    )

    def body_as_bytes(self):
        return pykern.pkjson.dump_bytes(self.body_as_dict())

    def body_as_dict(self):
        if "_body_as_dict" not in self:
            raise sirepo.util.BadRequest("no body")
        return self.get("_body_as_dict")

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

    def init_quest_for_child(self, child, parent):
        return (
            super()
            .init_quest_for_child(child, parent)
            .pkupdate(
                # need to cascade current value, not parent.sreq.cookie_state
                cookie_state=parent.cookie.export_state(),
                # no data yet; set_body will change
                http_method="GET",
            ),
        )

    def method_is_post(self):
        return self.http_method == "POST"

    def set_body(self, body):
        if "_body_as_dict" in self or "_body_as_bytes" in self:
            raise AssertionError(f"body may only be set once; new body={body}")
        if not isinstance(body, PKDict):
            raise AssertionError(f"invalid body type={type(body)} body={body}")
        self.http_method = "POST"
        self._body_as_dict = body


class _SRequestCLI(_SRequestBase):
    @classmethod
    def init_quest(cls, qcall, internal_req):
        return cls(qcall, internal_req=internal_req).pkupdate(
            cookie_state=None,
            http_authorization=None,
            http_headers=PKDict(),
            http_method="GET",
            http_server_uri="http://localhost/",
            remote_addr="0.0.0.0",
        )

    def set_log_user(self, log_user):
        pass


class _SRequestHTTP(_SRequestBase):
    @classmethod
    def init_quest(cls, qcall, internal_req):
        def _parse_authorization(value):
            if not value:
                return None
            try:
                t, i = value.split(None, 1)
                t = t.lower()
            except Exception:
                raise sirepo.util.Forbidden(
                    "unparseable authorization header={}", value
                )
            if t != "basic":
                raise sirepo.util.Forbidden("unhandled authorization type={}", t)
            try:
                u, p = base64.b64decode(i).split(b":", 1)
            except Exception:
                raise sirepo.util.Forbidden(
                    "unparseable authorization info={} type={}", i, t
                )
            return PKDict(
                type=t,
                username=pykern.pkcompat.from_bytes(u),
                password=pykern.pkcompat.from_bytes(p),
            )

        r = internal_req.request
        return cls(qcall, internal_req=internal_req).pkupdate(
            # Property that extracts the body so defer until use
            _body_as_bytes=lambda: r.body,
            cookie_state=r.headers.get("Cookie"),
            http_authorization=_parse_authorization(r.headers.get("Authorization")),
            http_headers=r.headers,
            http_method=r.method,
            http_request_uri=r.full_url(),
            http_server_uri=f"{r.protocol}://{r.host}/",
            remote_addr=sirepo.http_util.remote_ip(r),
        )

    def body_as_bytes(self):
        if "_body_as_dict" in self:
            return super().body_as_bytes()
        if "_body_as_bytes" not in self:
            raise sirepo.util.BadRequest("no body")
        return self._body_as_bytes()

    def body_as_dict(self):
        def _content_type_eq(value):
            c = _content_type()._key
            if c is None:
                return False
            return c.lower() == value.lower()

        def _content_type():
            if "_content_type" not in self:
                self._content_type = _parse_header(
                    self.header_uget("Content-Type") or ""
                )
            return self._content_type

        def _parse_header(line):
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
                    while (
                        end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2
                    ):
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
            rv = PKDict(_key=key)
            for name, decoded_value in decoded_params:
                value = email.utils.collapse_rfc2231_value(decoded_value)
                if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]
                rv[name] = value
            return rv

        if "_body_as_dict" in self:
            return super().body_as_dict()
        if not _content_type_eq(pykern.pkjson.MIME_TYPE):
            raise sirepo.util.BadRequest(
                "Content-Type={} must be {}",
                self.header_uget("Content-Type"),
                pykern.pkjson.MIME_TYPE,
            )
        return pykern.pkjson.load_any(self.body_as_bytes())

    def form_file_get(self):
        return _FormFileHTTP(self)

    def form_get(self, name, default):
        return self.internal_req.get_argument(name, default)

    def set_log_user(self, log_user):
        self.internal_req.sr_set_log_user(log_user)


class _SRequestWebSocket(_SRequestBase):
    @classmethod
    def init_quest(cls, qcall, internal_req):
        b = internal_req.get("body_as_dict")
        return cls(qcall, internal_req=internal_req).pkupdate(
            _body_as_dict=b,
            # This is not use except in api_errorLogging, which shouldn't happen much
            cookie_state=internal_req.handler.cookie_state,
            http_authorization=None,
            http_headers=internal_req.headers,
            http_method="POST" if b else "GET",
            http_server_uri=internal_req.handler.http_server_uri,
            remote_addr=internal_req.handler.remote_addr,
        )

    def form_file_get(self):
        return _FormFileWebSocket(self)

    def form_get(self, name, default):
        return self.body_as_dict().get(name, default)

    def set_log_user(self, log_user):
        self.internal_req.set_log_user(log_user)
