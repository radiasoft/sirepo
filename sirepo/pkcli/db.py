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
    # TODO(e-carlin): file path from supervisor
    _migrate_to_job('/home/vagrant/src/radiasoft/sirepo/run/supervisor-job')


def _migrate_to_job(db_dir):
    from pykern import pkio
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import job
    from sirepo import simulation_db
    import os
    import re
    pkdp('')

    _NEXT_REQUEST_SECONDS = PKDict({
        job.PARALLEL: 2,
        job.SBATCH: 60,  # TODO(e-carlin): how should this be set?
        job.SEQUENTIAL: 1,
    })

    _PARALLEL_STATUS_FIELDS = frozenset((
        'computeJobHash',
        'elapsedTime',
        'frameCount',
        'lastUpdateTime',
        'percentComplete',
        'computeJobStart',
    ))

    def _write_supervisor_status_file(data):
        db = PKDict(
            computeJid=data.computeJid,
            computeJobHash=data.computeJobHash,
            computeJobStart=0,
            computeJobQueued=0,
            error=None,
            history=[],
            isParallel=data.isParallel,
            jobRunMode=data.jobRunMode,
            lastUpdateTime=0,
            nextRequestSeconds=_NEXT_REQUEST_SECONDS[data.jobRunMode],
            simulationId=data.simulationId,
            simulationType=data.simulationType,
#TODO(robnagler) when would req come in with status?
            status=data.status,
            uid=data.uid,
        )
        if data.isParallel:
            db.parallelStatus = PKDict(
                ((k, 0) for k in _PARALLEL_STATUS_FIELDS),
            )

    def _db_file(computeJid):
        db_dir.join(computeJid + '.json')

    def _read_status_file(path):
        return pkio.read_text(path.join(job.RUNNER_STATUS_FILE))

    def _is_parallel(report_name):
        # TODO(e-carlin): is this valid?
        return bool(re.compile('animation', re.IGNORECASE).search(report_name))

    for u in pkio.sorted_glob(simulation_db.user_dir_name().join('*/')):
        for t in pkio.sorted_glob(u.join('*/')):
            if t.basename in ('adm', 'myapp'):
                continue
            for s in pkio.sorted_glob(t.join('*/')):
                if s.basename == 'lib':
                    continue
                # TODO(e-carlin): why is '*/' not listing only dirs?
                for r in [p for p in pkio.sorted_glob(s.join('*/')) if os.path.isdir(str(p))]:
                    pkdp(
                        'user={} simType={} simId={} report={} path={} status={} is_parallel={}',
                        u.basename,
                        t.basename,
                        s.basename,
                        r.basename,
                        r,
                        _read_status_file(r),
                        _is_parallel(r.basename),
                    )
