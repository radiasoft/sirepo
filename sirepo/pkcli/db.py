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


def populate_supervisor_state(db_dir, sbatch_poll_secs):
    from pykern import pkio
    from pykern.pkcollections import PKDict, json_load_any
    from pykern.pkdebug import pkdp
    from sirepo import job
    from sirepo import simulation_db
    from sirepo import util
    from sirepo import sim_data
    import sirepo.template
    import os
    import re

    db_dir = pkio.py_path(db_dir)
    pkio.mkdir_parent(db_dir)

    _NEXT_REQUEST_SECONDS = PKDict({
        job.PARALLEL: 2,
        job.SBATCH: int(sbatch_poll_secs),
        job.SEQUENTIAL: 1,
    })

    def _add_parallel_status(in_json, sim_data, run_dir, data):
        t = sirepo.template.import_module(data.simulationType)
        data.parallelStatus = PKDict(
           t.background_percent_complete(
               sim_data.parse_model(in_json),
               run_dir,
               False,
           )
        )

    def _create_supervisor_state_file(uid, run_dir):
        i = json_load_any(
            run_dir.join(
                sirepo.template.template_common.INPUT_BASE_NAME +
                simulation_db.JSON_SUFFIX
            )
        )
        c = sim_data.get_class(i.simulationType)
        p = _is_parallel(run_dir.basename)
        j = job.PARALLEL if p else job.SEQUENTIAL
        s, t = _read_status_file(run_dir)
        d = PKDict(
            computeJid=c.parse_jid(i, uid),
            computeJobHash=i.models.computeJobCacheKey.computeJobHash,
            computeJobQueued=0,
            computeJobStart=i.models.computeJobCacheKey.computeJobStart,
            error=None,
            history=[],
            isParallel=p,
            jobRunMode=j,
            lastUpdateTime=t,
            nextRequestSeconds=_NEXT_REQUEST_SECONDS[j],
            simulationId=i.models.simulation.simulationId,
            simulationType=i.simulationType,
            status=s,
            uid=uid,
        )
        if d.isParallel:
            _add_parallel_status(i, c, run_dir, d)
        util.json_dump(d, path=_db_file(d.computeJid))

    def _db_file(computeJid):
        return db_dir.join(computeJid + '.json')

    def _is_parallel(report_name):
        # TODO(e-carlin): is this valid?
        return bool(re.compile('animation', re.IGNORECASE).search(report_name))

    def _read_status_file(run_dir):
        p = path.join(job.RUNNER_STATUS_FILE)
        s = sirepo.job.COMPLETED if pkio.read_text(p) == sirepo.job.COMPLETED \
            else sirepo.job.MISSING
        return s, p.mtime()

    for path, dirs, files in os.walk(str(simulation_db.user_dir_name())):
        if not dirs and 'status' in files:
            path = pkio.py_path(path)
            _create_supervisor_state_file(
                simulation_db.uid_from_dir_name(pkio.py_path(path)),
                path,
            )
