# -*- coding: utf-8 -*-
"""Common functionality that is shared between the server, supervisor, and driver.

Because this is going to be shared across the server, supervisor, and driver it
must be py2 compatible.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
import sirepo.srdb
import sirepo.util
import re


OP_ANALYSIS = 'analysis'
OP_CANCEL = 'cancel'
OP_CONDITION = 'condition'
OP_ERROR = 'error'
OP_KILL = 'kill'
OP_OK = 'ok'
#: Agent indicates it is ready
OP_ALIVE = 'alive'
OP_RUN = 'run'

#: path supervisor registers to receive messages from agent
AGENT_URI = '/agent'

#: requests from the agent
AGENT_ABS_URI = None

#: path supervisor registers to receive requests from server
SERVER_URI = '/server'

#: requests from the flask server
SERVER_ABS_URI = None

#: path supervisor registers to receive requests from job_process for file PUTs
DATA_FILE_URI = '/data-file'

#: how jobs request files
LIB_FILE_URI = '/lib-file'

#: how jobs request list of files (relative to `LIB_FILE_URI`)
LIB_FILE_LIST_URI = '/list.json'

#: where user lib file directories are linked for static download (job_supervisor)
LIB_FILE_ROOT = None

#: where user data files come in (job_supervisor)
DATA_FILE_ROOT = None

#: where job_processes request files lib files for api_runSimulation
LIB_FILE_ABS_URI = None

#: where job_process will PUT data files for api_downloadDataFile
DATA_FILE_ABS_URI = None

#: how jobs request files (relative to `srdb.root`)
SUPERVISOR_SRV_SUBDIR = 'supervisor-srv'

#: how jobs request files (absolute)
SUPERVISOR_SRV_ROOT = None

DEFAULT_IP = '127.0.0.1' # use v3.radia.run when testing sbatch
DEFAULT_PORT = 8001

RUNNER_STATUS_FILE = 'status'

UNIQUE_KEY_RE = re.compile(r'^\w$')

CANCELED = 'canceled'
COMPLETED = 'completed'
ERROR = 'error'
MISSING = 'missing'
PENDING = 'pending'
RUNNING = 'running'

#: When the job is completed
EXIT_STATUSES = frozenset((CANCELED, COMPLETED, ERROR))

#: Valid values for job status
STATUSES = EXIT_STATUSES.union((PENDING, RUNNING))

# should come from schema
SEQUENTIAL = 'sequential'
PARALLEL = 'parallel'
SBATCH = 'sbatch'

#: valid jobRunMode values
RUN_MODES = frozenset((SEQUENTIAL, PARALLEL, SBATCH))

#: categories of jobs
KINDS = frozenset((SEQUENTIAL, PARALLEL))

cfg = None

def agent_cmd_stdin_env(cmd, env, pyenv='py3', cwd='.', source_bashrc=''):
    """Convert `cmd` in `pyenv` with `env` to script and cmd

    Uses tempfile so the file can be closed after the subprocess
    gets the handle. You have to close `stdin` after calling
    `tornado.process.Subprocess`, which calls `subprocess.Popen`
    inline, since it' not ``async``.

    Args:
        cmd (iter): list of words to be quoted
        env (str): empty or result of `agent_env`
        pyenv (str): python environment (py3 default)
        cwd (str): directory for the agent to run in (will be created if it doesn't exist)
        uid (str): which user should be logged in

    Returns:
        tuple: new cmd (tuple), stdin (file), env (PKDict)
    """
    import os
    import tempfile

    t = tempfile.TemporaryFile()
    c = 'exec ' + ' '.join(("'{}'".format(x) for x in cmd))
    # POSIT: we control all these values
    t.write(
        '''{}
set -e
mkdir -p '{}'
cd '{}'
pyenv shell {}
{}
{}
'''.format(
        source_bashrc,
        cwd,
        cwd,
        pyenv,
        env or agent_env(),
        c,
    ).encode())
    t.seek(0)
    # it's reasonable to hardwire this path, even though we don't
    # do that with others. We want to make sure the subprocess starts
    # with a clean environment (no $PATH). You have to pass HOME.
    return ('/bin/bash', '-l'), t, PKDict(HOME=os.environ['HOME'])


def agent_env(env=None, uid=None):
    env = (env or PKDict()).pksetdefault(
        **pkconfig.to_environ((
            'pykern.*',
            'sirepo.feature_config.job_supervisor',
            'sirepo.simulation_db.sbatch_display',
        ))
    ).pksetdefault(
        PYTHONPATH='',
        PYTHONUNBUFFERED='1',
        SIREPO_AUTH_LOGGED_IN_USER=lambda: uid or sirepo.auth.logged_in_user(),
        SIREPO_SRDB_ROOT=lambda: sirepo.srdb.root(),
    )
    return '\n'.join(("export {}='{}'".format(k, v) for k, v in env.items()))

def init():
    global cfg

    if cfg:
        return
    cfg = pkconfig.init(
        supervisor_uri=(
            'http://{}:{}'.format(DEFAULT_IP, DEFAULT_PORT),
            str,
            'supervisor base uri',
        ),
    )
    global SUPERVISOR_SRV_ROOT, LIB_FILE_ROOT, DATA_FILE_ROOT, \
        LIB_FILE_ABS_URI, DATA_FILE_ABS_URI, AGENT_ABS_URI, SERVER_ABS_URI

    SUPERVISOR_SRV_ROOT = sirepo.srdb.root().join(SUPERVISOR_SRV_SUBDIR)
    LIB_FILE_ROOT = SUPERVISOR_SRV_ROOT.join(LIB_FILE_URI[1:])
    DATA_FILE_ROOT = SUPERVISOR_SRV_ROOT.join(DATA_FILE_URI[1:])
    # trailing slash necessary
    LIB_FILE_ABS_URI = cfg.supervisor_uri + LIB_FILE_URI + '/'
    DATA_FILE_ABS_URI = cfg.supervisor_uri + DATA_FILE_URI + '/'
#TODO(robnagler) figure out why we need ws (wss, implicit)
    AGENT_ABS_URI = cfg.supervisor_uri.replace('http', 'ws', 1) + AGENT_URI
    SERVER_ABS_URI = cfg.supervisor_uri + SERVER_URI


def init_by_server(app):
    """Initialize module"""
    init()

    from sirepo import job_api
    from sirepo import uri_router

    uri_router.register_api_module(job_api)


def unique_key():
    return sirepo.util.random_base62(32)


#TODO(robnagler) consider moving this into pkdebug
class LogFormatter:
    """Convert arbitrary objects to length-limited strings"""

    #: maximum length of elements or total string
    MAX_STR = 2000

    #: maximum number of elements
    MAX_LIST = 10

    SNIP = '[...]'

    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        def _s(s):
            s = str(s)
            return s[:self.MAX_STR] + (s[self.MAX_STR:] and self.SNIP)

        def _j(values, delims):
            v = list(values)
            return delims[0] + ' '.join(
                v[:self.MAX_LIST] + (v[self.MAX_LIST:] and [self.SNIP])
            ) + delims[1]

        if isinstance(self.obj, dict):
            return _j(
                (_s(k) + ': ' + _s(v) for k, v in self.obj.items() \
                    if k not in ('result', 'arg')),
                '{}',
            )
        if isinstance(self.obj, (tuple, list)):
            return _j(
                (_s(v) for v in self.obj),
                '[]' if isinstance(self.obj, list) else '()',
            )
        return _s(self.obj)
