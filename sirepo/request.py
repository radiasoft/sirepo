# -*- coding: utf-8 -*-
"""Requests hold context for API calls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import email.utils
import pykern.pkcompat
import sirepo.quest
import sirepo.util
import user_agents


_POST_ATTR = "sirepo_http_request_post"

_SIM_TYPE_ATTR = "sirepo_http_request_sim_type"


def qcall_init(qcall):
    import flask

    sreq = Base(
        http_authorization=flask.request.authorization,
        http_headers=flask.request.headers,
        http_method=flask.request.method,
        http_request_uri=flask.request.url,
        http_server_uri=flask.url_for("_dispatch_empty", _external=True),
        internal_req=flask.request,
        remote_addr=flask.request.remote_addr,
    )
    qcall.attr_set("sreq", sreq)


class Base(sirepo.quest.Attr):
    """Holds context for incoming requests"""

    def body_as_bytes(self):
        return self._internal_req.get_data(cache=False)

    def content_type_encoding(self):
        return self.__content_type().get("charset")

    def content_type_eq(self, value):
        return self.__content_type()._key.lower() == value.lower()

    def header_uget(self, key):
        return self.http_headers.get(key)

    def is_spider(self):
        a = self.http_header("User-Agent")
        if not a:
            # assume it's a spider if there's no header
            return True
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
                self.http_header("Content-Type") or ""
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
