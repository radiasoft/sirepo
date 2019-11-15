# -*- coding: utf-8 -*-
"""Common functionality that is shared between the server, supervisor, and driver.

Because this is going to be shared across the server, supervisor, and driver it
must be py2 compatible.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
import aenum
import sirepo.util


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

#: path supervisor registers to receive requests from server
SERVER_URI = '/server'

#: path supervisor registers to receive requests from job_process for file PUTs
DATA_FILE_URI = '/file'

#: how jobs request files
JOB_FILE_URI = '/job-file'

#: how jobs request list of files (relative to `JOB_FILE_URI`)
JOB_FILE_LIST_URI = '/files.json'

#: how jobs request files (relative to `srdb.root`)
JOB_FILE_DIR = 'supervisor-srv'

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 8001

RUNNER_STATUS_FILE = 'status'

CANCELED = 'canceled'
COMPLETED = 'completed'
ERROR = 'error'
MISSING = 'missing'
PENDING = 'pending'
RUNNING = 'running'
#: Valid values for job status
STATUSES = frozenset((CANCELED, COMPLETED, ERROR, MISSING, PENDING, RUNNING))

SEQUENTIAL = 'sequential'
PARALLEL = 'parallel'

#: categories of jobs
KINDS = frozenset((SEQUENTIAL, PARALLEL))

cfg = None

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
    pkdc('cfg={}', cfg)


def subprocess_cmd_stdin_env(cmd, env, pyenv='py3'):
    """Convert `cmd` in `pyenv` with `env` to script and cmd

    Uses tempfile so the file can be closed after the subprocess
    gets the handle. You have to close `stdin` after calling
    `tornado.process.Subprocess`, which calls `subprocess.Popen`
    inline, since it' not ``async``.

    Args:
        cmd (iter): list of words to be quoted
        env (PKDict): environment to pass
        pyenv (str): python environment (py3 default)

    Returns:
        tuple: new cmd (list) and stdin (file)
    """
    import tempfile
#TODO(robnagler) pykern shouldn't convert these to objects, rather leave as strings
#  then we'd refer to them. Perhaps that's not realistic, and pkconfig should
#  keep a shadow which can be retrieved.
    for k in 'CONTROL', 'OUTPUT', 'REDIRECT_LOGGING', 'WANT_PID_TIME':
        k = 'PYKERN_PKDEBUG_' + k
        v = os.environ.get(k)
        if v:
            env.pksetdefault(k, v)
    env.pksetdefault(
        PYKERN_PKCONFIG_CHANNEL=pkconfig.cfg.channel,
    )
    # POSIT: we control all these values
    e =
    c =
    s = '''
set -e
pyenv shell {}
{}
exec {}
'''.format(
        '\n'.join(("export {}='{}'".format(k, v) for k, v in env)),
        pyenv,
        ' '.join(("'{x}'" for x in cmd)),
    )
    t = tempfile.TemporaryFile()
    t.seek(0)
    return ['/bin/bash', '-l'], t, PKDict()



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
