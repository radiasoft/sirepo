# -*- coding: utf-8 -*-
"""Run Python processes in background

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import multiprocessing
import re
import sirepo.const
import sys

FIRST_RANK = 0


def abort_on_signal_code():
    return """

from mpi4py import MPI
if MPI.COMM_WORLD.Get_rank():
    import signal
    signal.signal(signal.SIGTERM, lambda x, y: MPI.COMM_WORLD.Abort(1))

"""


def cfg():
    return _cfg


def get_cmd():
    c = ["python", "parameters.py"]
    return c if _cfg.in_slurm else _mpiexec_cmd() + c


def restrict_op_to_first_rank(op):
    """If the process has rank FIRST_RANK, call a function. Otherwise do nothing.

    Use this to call a function that will cause conflicts if called by multiple processes,
    such as writing results to a file

    Args:
        op (function): function to call

    Returns:
        object: result of `op`
    """
    c = None
    r = FIRST_RANK
    res = None
    try:
        import mpi4py.MPI

        c = mpi4py.MPI.COMM_WORLD
        if c.Get_size() > 1:
            r = c.Get_rank()
        else:
            c = None
    except Exception:
        pass
    if r == FIRST_RANK:
        try:
            res = op()
        except Exception as e:
            if c:
                c.Abort(1)
            raise
    if c:
        res = c.bcast(res, root=FIRST_RANK)
    return res


def restrict_ops_to_first_node(ops):
    """Run `ops` in parallel on available cores on the first node

    This functions uses `multiprocessing` to run `ops`. If run under
    MPI, will run instantiate the multiprocessing.Pool in the first
    rank only, and the other MPI ranks (processes) will remain idle
    until all `ops` have been run.

    Note that processes originate from the first rank MPI process so
    they share the first rank's memory up until multiprocessing spawns
    each op.

    Args:
        ops (iterable): produces callables that will be run in parallel

    """

    def _run():
        # TODO(robnagler): if run on multiple machines, cores need to be tasks_per_node
        with multiprocessing.Pool(_cfg.cores, maxtasksperchild=1) as p:
            p.map(_globalize_op, ops)

    restrict_op_to_first_rank(_run)


def run_program(cmd, output=sirepo.const.MPI_LOG, env=None):
    """Execute python script with mpi.

    Args:
        cmd (list): cmd to run
        output (str): where to write stdout and stderr
        env (dict): what to pass as env
    """
    pksubprocess.check_call_with_signals(
        _mpiexec_cmd() + cmd,
        msg=pkdlog,
        output=str(output),
        env=env,
    )


def run_script(script):
    """Execute python script with mpi.

    Args:
        script (str): python text
    """
    a = abort_on_signal_code()
    n = re.sub(r"^from __future.*", a, script, count=1, flags=re.MULTILINE)
    script = a + script if n == script else n
    fn = "mpi_run.py"
    pkio.write_text(fn, script)
    run_program([sys.executable or "python", fn])


def _globalize_op(op):
    """Runs `op` in global namespace for multiprocessing"""
    return op()


def _mpiexec_cmd():
    return [
        "mpiexec",
        "--bind-to",
        "none",
        "-n",
        str(_cfg.cores),
    ]


_cfg = pkconfig.init(
    cores=(1, int, "cores to use per run"),
    in_slurm=(False, bool, "True if being run by slurm"),
)
