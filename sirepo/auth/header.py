# -*- coding: utf-8 -*-
"""HTTP Header Auth Login

:copyright: Copyright (c) 2019 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkconfig


AUTH_METHOD = "header"

AUTH_METHOD_VISIBLE = True


def init_apis(*args, **kwargs):
    global _cfg
    _cfg = pkconfig.init(
        tkn=pkconfig.Required(str, "Token value used in place of the password"),
    )


def require_user(self):
    """Check for the header with the configured name and resolve the uid from it"""
    def _user(email):
        m = self.auth_db.model("AuthEmailUser")
        u = m.unchecked_search_by(unverified_email=email)
        if u:
            return u
        u = m.new(unverified_email=email, user_name=email)
        u.save()
        return m.unchecked_search_by(unverified_email=email)

    v = self.sreq.get("http_authorization")
    if v and v.type == "basic" and v.password == _cfg.tkn:
        u = _user(v.username)
        if not u:
            pkdlog("No user found for email={}", v.username)
            return None
        else:
            return u.uid        
    return None
