# -*- coding: utf-8 -*-
u"""Database upgrade management

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkinspect, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import os
import sirepo.auth
import sirepo.auth_db
import sirepo.job
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.srtime
import sirepo.template
import sirepo.util


def do_all():
    a = sirepo.auth_db.DbUpgrade.search_all_for_column('name')
    f = pkinspect.module_functions('_2')
    for n in sorted(set(f.keys()) - set(a)):
        f[n]()
        sirepo.auth_db.DbUpgrade(
            name=n,
            created=sirepo.srtime.utc_now(),
        ).save()


def _20210211_add_flash_proprietary_lib_files():
    """Add proprietary lib files to existing FLASH users' lib dir"""

    if not sirepo.template.is_sim_type('flash'):
        return
    for u in sirepo.auth_db.all_uids():
        # Remove the existing rpm
        with sirepo.auth.set_user(u):
            pkio.unchecked_remove(sirepo.simulation_db.simulation_lib_dir(
                'flash',
            ).join('flash.rpm'))
        # Add's the flash proprietary lib files (unpacks flash.tar.gz)
        sirepo.auth_db.audit_proprietary_lib_files(u)


def _20210211_upgrade_runner_to_job_db():
    """Create the job supervisor db state files"""

    def _add_compute_status(run_dir, data):
        p = run_dir.join(sirepo.job.RUNNER_STATUS_FILE)
        data.pkupdate(
            lastUpdateTime=int(p.mtime()),
            status=pkio.read_text(p),
        )

    def _add_parallel_status(in_json, sim_data, run_dir, data):
        t = sirepo.template.import_module(data.simulationType)
        # pksetdefault emulates job_cmd._background_percent_complete
        data.parallelStatus = PKDict(
            t.background_percent_complete(
                sim_data.parse_model(in_json),
                run_dir,
                False,
            )
        ).pksetdefault(
            lastUpdateTime=data.lastUpdateTime,
            frameCount=0,
            percentComplete=0.0,
        )

    def _create_supervisor_state_file(run_dir):
        try:
            i, t = _load_in_json(run_dir)
        except Exception as e:
            if pkio.exception_is_not_found(e):
                return
            raise
        u = sirepo.simulation_db.uid_from_dir_name(run_dir)
        sirepo.auth.cfg.logged_in_user = u
        c = sirepo.sim_data.get_class(i.simulationType)
        d = PKDict(
            computeJid=c.parse_jid(i, u),
            computeJobHash=c.compute_job_hash(i), # TODO(e-carlin): Another user cookie problem
            computeJobSerial=t,
            computeJobStart=t,
            computeModel=c.compute_model(i),
            error=None,
            history=[],
            isParallel=c.is_parallel(i),
            simulationId=i.simulationId,
            simulationType=i.simulationType,
            uid=u,
        )
        d.pkupdate(
            jobRunMode=sirepo.job.PARALLEL if d.isParallel else sirepo.job.SEQUENTIAL,
            nextRequestSeconds=c.poll_seconds(i),
        )
        _add_compute_status(run_dir, d)
        if d.status not in (sirepo.job.COMPLETED, sirepo.job.CANCELED):
            return

        if d.isParallel:
            _add_parallel_status(i, c, run_dir, d)
        sirepo.util.json_dump(d, path=_db_file(d.computeJid))

    def _db_file(computeJid):
        return db_dir.join(computeJid + '.json')

    def _load_in_json(run_dir):
        p = sirepo.simulation_db.json_filename(
            sirepo.template.template_common.INPUT_BASE_NAME,
            run_dir
        )
        c = sirepo.simulation_db.read_json(p)
        return c, c.computeJobCacheKey.computeJobStart if \
            c.get('computejobCacheKey') else \
            int(p.mtime())

    db_dir = sirepo.srdb.supervisor_dir()
    if not sirepo.simulation_db.user_path().exists():
        pkio.mkdir_parent(db_dir)
        return
    if db_dir.exists():
        return
    pkdlog('db_dir={}', db_dir)
    c = 0
    pkio.mkdir_parent(db_dir)
    for f in pkio.walk_tree(
            sirepo.simulation_db.user_path(),
            '^(?!.*src/).*/{}$'.format(sirepo.job.RUNNER_STATUS_FILE),

    ):
        try:
            _create_supervisor_state_file(pkio.py_path(f.dirname))
        except Exception as e:
            c += 1
            k = PKDict(run_dir=f)
            s = 'run_dir={run_dir}'
            if c < 50:
                k.stack = pkdexc()
                s += ' stack={stack}'
            else:
                k.error = getattr(e, 'args', []) or e
                s += ' error={error}'
            pkdlog(s, **k)
