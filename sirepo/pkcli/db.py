# -*- coding: utf-8 -*-
u"""Database utilities

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def upgrade():
    """Upgrade the database"""
    from pykern import pkio
    from sirepo import simulation_db
    from sirepo import server
    import re

    def _inc(m):
        return m.group(1) + str(int(m.group(2)) + 1)

    server.init()
    for d in pkio.sorted_glob(simulation_db.user_dir_name().join('*/warppba')):
        for fn in pkio.sorted_glob(d.join('*/sirepo-data.json')):
            with open(str(fn)) as f:
                t = f.read()
            for old, new in (
                ('"WARP example laser simulation"', '"Laser-Plasma Wakefield"'),
                ('"Laser Pulse"', '"Laser-Plasma Wakefield"'),
                ('"WARP example electron beam simulation"', '"Electron Beam"'),
            ):
                if not old in t:
                    continue
                t = t.replace(old, new)
                t = re.sub(r'(simulationSerial":\s+)(\d+)', _inc, t)
                break
            with open(str(fn), 'w') as f:
                f.write(t)


def upgrade_runner_to_job_db(db_dir):
    import sirepo.auth
    from pykern import pkio
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import job
    from sirepo import simulation_db
    from sirepo import sim_data
    from sirepo import util
    import pykern.pkio
    import sirepo.template

    db_dir = pkio.py_path(db_dir)
    pkio.mkdir_parent(db_dir)

    def _add_compute_status(run_dir, data):
        s, t = _read_status_file(run_dir)
        data.pkupdate(
            lastUpdateTime=t,
            status=s,
        )

    def _add_parallel_status(in_json, sim_data, run_dir, data):
        t = sirepo.template.import_module(data.simulationType)
        data.parallelStatus = PKDict(
           t.background_percent_complete(
               sim_data.parse_model(in_json),
               run_dir,
               False,
           )
        )

    def _create_supervisor_state_file(run_dir):
        try:
            i, t = _load_in_json(run_dir)
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                return
            raise
        u = simulation_db.uid_from_dir_name(run_dir)
        sirepo.auth.cfg.logged_in_user = u
        c = sim_data.get_class(i.simulationType)
        d = PKDict(
            computeJid=c.parse_jid(i, u),
            computeJobHash=c.compute_job_hash(i), # TODO(e-carlin): Another user cookie problem
            computeJobQueued=t,
            computeJobStart=t,
            error=None,
            history=[],
            isParallel=c.is_parallel(i),
            simulationId=i.simulationId,
            simulationType=i.simulationType,
            uid=u,
        )
        d.pkupdate(
            jobRunMode=job.PARALLEL if d.isParallel else job.SEQUENTIAL,
            nextRequestSeconds=c.poll_seconds(i),
        )
        _add_compute_status(run_dir, d)

        if (
            d.status in (sirepo.job.COMPLETED, sirepo.job.CANCELED)
            and d.isParallel
        ):
            _add_parallel_status(i, c, run_dir, d)
        util.json_dump(d, path=_db_file(d.computeJid))

    def _db_file(computeJid):
        return db_dir.join(computeJid + '.json')

    def _load_in_json(run_dir):
        p = simulation_db.json_filename(
            sirepo.template.template_common.INPUT_BASE_NAME,
            run_dir
        )
        c = simulation_db.read_json(p)
        return c, c.computeJobCacheKey.computeJobStart if \
            c.get('computejobCacheKey') else \
            p.mtime()

    def _read_status_file(run_dir):
        p = run_dir.join(job.RUNNER_STATUS_FILE)
        s = sirepo.job.COMPLETED if pkio.read_text(p) == sirepo.job.COMPLETED \
            else sirepo.job.MISSING
        return s, p.mtime()
    try:
        for f in pkio.walk_tree(
                simulation_db.user_dir_name(),
                '/' + sirepo.job.RUNNER_STATUS_FILE + '$'
        ):
            _create_supervisor_state_file(pkio.py_path(f.dirname))
    except Exception:
        db_dir.remove()
        raise
