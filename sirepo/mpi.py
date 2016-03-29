# -*- coding: utf-8 -*-
"""Run Python processes in background

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkdebug import pkdp
from sirepo.template import template_common
import os
import re
import signal
import subprocess
import sys


def run(script):
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
    try:
        cmd = [
            'mpiexec',
            '-n',
            str(cfg.slaves),
            sys.executable or 'python',
            fn,
        ]
        p = subprocess.Popen(
            cmd,
            stdin=open(os.devnull),
            stdout=open('mpi_run.out', 'w'),
            stderr=subprocess.STDOUT,
        )
        pkdp('Started: {} {}', p.pid, cmd)
        signal.signal(signal.SIGTERM, lambda x, y: p.terminate())
        rc = p.wait()
        if rc != 0:
            p = None
            raise RuntimeError('child terminated: retcode={}'.format(rc))
        pkdp('Stopped: {} {}', pid, cmd)
    finally:
        if not p is None:
            pkdp('Terminating: {} {}', p.pid, cmd)
            p.terminate()


cfg = pkconfig.init(
    slaves=(1, int, 'cores to use per run'),
)
