# -*- coding: utf-8 -*-
"""NSLS-II BlueSky Login

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import simulation_db
from sirepo import util
import base64
import hashlib
import sirepo.quest
import time


AUTH_METHOD = "bluesky"

#: bots only
AUTH_METHOD_VISIBLE = False

#: module handle
this_module = pkinspect.this_module()

#: separates the values of the clear text for the hash
# POSIT: ':' not part of simulationType or simulationId
_AUTH_HASH_SEPARATOR = ":"

#: half the window length for replay attacks
_AUTH_NONCE_REPLAY_SECS = 10

#: separates the time stamp from the uniqifier in the nonce
_AUTH_NONCE_SEPARATOR = "-"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("allow_cookieless_set_user", sid="SimId")
    def api_authBlueskyLogin(self):
        req = self.parse_post(id=True)
        auth_hash(req.req_data, verify=True)
        path = simulation_db.find_global_simulation(
            req.type,
            req.id,
            checked=True,
        )
        self.auth.login(
            this_module,
            uid=simulation_db.uid_from_dir_name(path),
            # do not supply sim_type (see auth.login)
        )
        return self.reply_ok(
            PKDict(
                data=simulation_db.open_json_file(req.type, sid=req.id, qcall=self),
                schema=simulation_db.get_schema(req.type),
            ),
        )

    @sirepo.quest.Spec("allow_cookieless_set_user")
    def api_blueskyAuth(self):
        """Deprecated use `api_authBlueskyLogin`"""
        return self.api_authBlueskyLogin()

    @sirepo.quest.Spec("require_user")
    def api_runSimulationBluesky(self):
        import os
        import pykern.pkio
        import sirepo.auth
        import subprocess

        d = self.parse_post(
            fixup_old_data=True,
            id=True,
            model=True,
            check_sim_exists=True,
        ).req_data
        run_dir = simulation_db.simulation_run_dir(d, qcall=self)
        pykern.pkio.unchecked_remove(run_dir)
        pykern.pkio.mkdir_parent(run_dir)

        # # TODO(pjm): need to hack in uid because prepare_simulation() below
        # #            doesn't use qcall
        # TODO(pjm): it may be better to call a subprocess with
        #            SIREPO_SIMULATION_DB_LOGGED_IN_USER set
        uid = sirepo.auth._Auth(qcall=self).logged_in_user()
        try:
            # prepare_simulation() doesn't use qcall
            if not simulation_db._cfg:
                simulation_db._cfg = PKDict()
            simulation_db._cfg.logged_in_user = uid
            simulation_db.prepare_simulation(d, run_dir)
        finally:
            simulation_db._cfg = None

        # # TODO(pjm): copied from pykern.pksubprocess
        stdout = open(str(run_dir.join("bluesky.log")), "w")
        stderr = subprocess.STDOUT
        subprocess.Popen(
            ["sirepo", d.simulationType, "run", str(run_dir)],
            stdin=open(os.devnull),
            stdout=stdout,
            stderr=stderr,
            cwd=str(run_dir),
            env=PKDict(os.environ).pkupdate(
                # special env to let runner optimize for bluesky, ex. not process output
                SIREPO_AUTH_BLUESKY_RUNNER="1",
            ),
        ).wait()
        stdout.close()
        # #####

        return self.reply_file(
            run_dir.join(
                sirepo.template.import_module(d.simulationType).get_data_file(
                    run_dir,
                    d.report,
                    d.fileIndex,
                    options=PKDict(suffix=""),
                )
            ),
        )


def auth_hash(http_post, verify=False):
    now = int(time.time())
    if not "authNonce" in http_post:
        if verify:
            raise util.Unauthorized("authNonce: missing field in request")
        http_post.authNonce = str(now) + _AUTH_NONCE_SEPARATOR + util.random_base62()
    h = hashlib.sha256()
    h.update(
        pkcompat.to_bytes(
            _AUTH_HASH_SEPARATOR.join(
                [
                    http_post.authNonce,
                    http_post.simulationType,
                    http_post.simulationId,
                    cfg.secret,
                ]
            )
        ),
    )
    res = "v1:" + pkcompat.from_bytes(
        base64.urlsafe_b64encode(h.digest()),
    )
    if not verify:
        http_post.authHash = res
        return
    if res != http_post.authHash:
        raise util.Unauthorized(
            "{}: hash mismatch expected={} nonce={}",
            http_post.authHash,
            res,
            http_post.authNonce,
        )
    t = http_post.authNonce.split(_AUTH_NONCE_SEPARATOR)[0]
    try:
        t = int(t)
    except ValueError as e:
        raise util.Unauthorized(
            "{}: auth_nonce prefix not an int: nonce={}",
            t,
            http_post.authNonce,
        )
    delta = now - t
    if abs(delta) > _AUTH_NONCE_REPLAY_SECS:
        raise util.Unauthorized(
            "{}: auth_nonce time outside replay window={} now={} nonce={}",
            t,
            _AUTH_NONCE_REPLAY_SECS,
            now,
            http_post.authNonce,
        )


cfg = pkconfig.init(
    secret=pkconfig.Required(
        str,
        "Shared secret between Sirepo and BlueSky server",
    ),
)
