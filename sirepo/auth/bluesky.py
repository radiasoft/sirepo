# -*- coding: utf-8 -*-
u"""NSLS-II BlueSky Login

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import http_reply
from sirepo import http_request
from sirepo import simulation_db
from sirepo import util
import base64
import hashlib
import time


#: configuration
cfg = None

AUTH_METHOD = 'bluesky'

#: bots only
AUTH_METHOD_VISIBLE = False

#: module handle
this_module = pkinspect.this_module()

#: separates the values of the clear text for the hash
# POSIT: ':' not part of simulationType or simulationId
_AUTH_HASH_SEPARATOR = ':'

#: half the window length for replay attacks
_AUTH_NONCE_REPLAY_SECS = 10

#: separates the time stamp from the uniqifier in the nonce
_AUTH_NONCE_SEPARATOR = '-'


@api_perm.allow_cookieless_set_user
def api_authBlueskyLogin():
    req = http_request.parse_json()
    auth_hash(req, verify=True)
    sid = req.simulationId
    sim_type = req.simulationType
    path = simulation_db.find_global_simulation(
        sim_type,
        sid,
        checked=True,
    )
    r = auth.login(
        this_module,
        uid=simulation_db.uid_from_dir_name(path),
    )
    if r:
        return r
    return http_reply.gen_json_ok(dict(
        data=simulation_db.open_json_file(req.simulationType, sid=req.simulationId),
        schema=simulation_db.get_schema(req.simulationType),
    ))


@api_perm.allow_cookieless_set_user
def api_blueskyAuth():
    """Deprecated use `api_authBlueskyLogin`"""
    return api_authBlueskyLogin()


def auth_hash(req, verify=False):
    now = int(time.time())
    if not 'authNonce' in req:
        if verify:
           util.raise_unauthorized('authNonce: missing field in request')
        req.authNonce = str(now) + _AUTH_NONCE_SEPARATOR + util.random_base62()
    h = hashlib.sha256()
    h.update(
        _AUTH_HASH_SEPARATOR.join([
            req.authNonce,
            req.simulationType,
            req.simulationId,
            cfg.secret,
        ]),
    )
    res = 'v1:' + base64.urlsafe_b64encode(h.digest())
    if not verify:
        req.authHash = res
        return
    if res != req.authHash:
        util.raise_unauthorized(
            '{}: hash mismatch expected={} nonce={}',
            req.authHash,
            res,
            req.authNonce,
        )
    t = req.authNonce.split(_AUTH_NONCE_SEPARATOR)[0]
    try:
        t = int(t)
    except ValueError as e:
        util.raise_unauthorized(
            '{}: auth_nonce prefix not an int: nonce={}',
            t,
            req.authNonce,
        )
    delta = now - t
    if abs(delta) > _AUTH_NONCE_REPLAY_SECS:
        util.raise_unauthorized(
            '{}: auth_nonce time outside replay window={} now={} nonce={}',
            t,
            _AUTH_NONCE_REPLAY_SECS,
            now,
            req.authNonce,
        )


def init_apis(*args, **kwargs):
    global cfg
    cfg = pkconfig.init(
        secret=pkconfig.Required(
            str,
            'Shared secret between Sirepo and BlueSky server',
        ),
    )
