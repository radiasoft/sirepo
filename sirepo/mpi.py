# -*- coding: utf-8 -*-
"""Run Python processes in background

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import re
import sys


def restrict_op_to_first_rank(op):
    c = None
    r = 0
    res = None
    try:
        import mpi4py.MPI
        c = mpi4py.MPI.COMM_WORLD
        if c.Get_size() > 1:
            r = c.Get_rank()
    except Exception:
        pass
    if r == 0:
        try:
            res = op()
        except Exception as e:
            pkdlog('op={} exception={} stack={}', op, e, pkdexc())
            if c:
                c.Abort(1)
            raise e
    if c:
        res = c.bcast(res, root=0)
    return res


def run_program(cmd, output='mpi_run.out', env=None):
    """Execute python script with mpi.

    Args:
        cmd (list): cmd to run
        output (str): where to write stdout and stderr
        env (dict): what to pass as env
    """
    cmd = [
        'mpiexec',
        '--bind-to',
        'none',
        '-n',
        str(cfg.cores),

    ] + cmd
    pksubprocess.check_call_with_signals(
        cmd,
        msg=pkdlog,
        output=str(output),
        env=env,
    )


def run_script(script):
    """Execute python script with mpi.

    Args:
        script (str): python text
    """
    abort = '''

from mpi4py import MPI
if MPI.COMM_WORLD.Get_rank():
    import signal
    signal.signal(signal.SIGTERM, lambda x, y: MPI.COMM_WORLD.Abort(1))

'''
    n = re.sub(r'^from __future.*', abort, script, count=1, flags=re.MULTILINE)
    script = abort + script if n == script else n
    fn = 'mpi_run.py'
    pkio.write_text(fn, script)
    p = None
    run_program([sys.executable or 'python', fn])


cfg = pkconfig.init(
    cores=(1, int, 'cores to use per run'),
    slaves=(1, int, 'DEPRECATED: set $SIREPO_MPI_CORES'),
)
cfg.cores = max(cfg.cores, cfg.slaves)
