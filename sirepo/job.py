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
import uuid


# Actions that the sirepo server, supervisor, or driver may send.
# TODO(e-carlin): Can we use an enum without manually serializing
# and deserializing?
#rn remove the word _JOB
ACTION_CANCEL = 'cancel'
ACTION_STATUS = 'status'
ACTION_ERROR = 'error'
ACTION_KEEP_ALIVE = 'keep_alive'
ACTION_KILL = 'kill'
ACTION_READY_FOR_WORK = 'ready_for_work'
#rn structure should be same "run" or "start"
ACTION_ANALYSIS = 'analysis'
ACTION_COMPUTE = 'compute'
ACTION_RUN_SIMULATION = 'runSimulation'

# Bidirectional operations
OP_ANALYSIS = 'analysis'
OP_CANCEL = 'cancel'
OP_CONDITION = 'condition'
OP_COMPUTE_STATUS = 'compute_status'
OP_ERROR = 'error'
OP_KILL = 'kill'
OP_OK = 'ok'
OP_RUN = 'run'
OP_STATUS = 'status'

#: path supervisor registers to receive messages from agent
AGENT_URI = '/agent'

#: path supervisor registers to receive requests from server
SERVER_URI = '/server'

DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 8001

RUNNER_STATUS_FILE = 'status'

cfg = None


# TODO(e-carlin): Use enums or string constants (like ACTIONS) not both.
class Status(aenum.Enum):
    #: data on disk exists, but is incomplete
    CANCELED = 'canceled'
    #: data on disk exists, and is fully usable
    COMPLETED = 'completed'
    #: data on disk exists, but job failed somehow
    ERROR = 'error'
    #: no data on disk, not currently running
    MISSING = 'missing'
    #: job has been sent to supervisor but hasn't started running
    PENDING = 'pending'
    #: data on disk is incomplete but it's running
    RUNNING = 'running'

#: run_status will not re-run a simulation in these states
ALREADY_GOOD_STATUS = (Status.RUNNING, Status.COMPLETED)


def init():
    global cfg

    if cfg:
        return
    cfg = pkconfig.init(
        supervisor_uri=(
            'http://{}:{}{}'.format(DEFAULT_IP, DEFAULT_PORT, SERVER_URI),
            str,
            'for supervisor requests',
        ),
    )
    pkdp('cfg set {}', cfg)


def init_by_server(app):
    """Initialize module"""
    init()

    from sirepo import job_api
    from sirepo import uri_router

    uri_router.register_api_module(job_api)


def unique_key():
    return str(uuid.uuid4())


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
