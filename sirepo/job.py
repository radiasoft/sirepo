"""Common functionality that is shared between the server, supervisor, and driver.

:copyright: Copyright (c) 2019-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
import pykern.pkcompat
import pykern.pkdebug
import sirepo.const
import sirepo.feature_config
import sirepo.srdb
import sirepo.util
import re

ERROR_CODE_RESPONSE_TOO_LARGE = "response_too_large"

OP_ANALYSIS = "analysis"
OP_CANCEL = "cancel"
OP_ERROR = "error"
OP_IO = "io"
OP_JOB_CMD_STDERR = "job_cmd_stderr"
OP_KILL = "kill"
OP_OK = "ok"
#: Agent indicates it is ready
OP_ALIVE = "alive"
OP_RUN = "run"
OP_RUN_STATUS = "run_status"
OP_RUN_STATUS_UPDATE = "run_status_update"
OP_SBATCH_AGENT_READY = "sbatch_agent_ready"
OP_SBATCH_LOGIN = "sbatch_login"
OP_BEGIN_SESSION = "begin_session"

#: Ops which don't need slot allocations or supervisor does not send
OPS_WITHOUT_SLOTS = frozenset(
    (
        OP_ALIVE,
        OP_BEGIN_SESSION,
        OP_CANCEL,
        OP_ERROR,
        OP_KILL,
        OP_OK,
        OP_RUN_STATUS,
        OP_SBATCH_AGENT_READY,
        OP_SBATCH_LOGIN,
    )
)

#: Types of slots required by op types
CPU_SLOT_OPS = frozenset((OP_ANALYSIS, OP_RUN))
#: All ops that have slots (see job_driver.DriverBase._slots_ready)
SLOT_OPS = frozenset().union(*[CPU_SLOT_OPS, (OP_IO,)])

#: state value (other states are implicit statuses)
STATE_OK = "ok"

_OK_REPLY = PKDict(state=STATE_OK)

#: path supervisor registers to receive messages from agent
AGENT_URI = "/job-agent-websocket"

#: path supervisor registers to receive srtime adjustments from server
SERVER_SRTIME_URI = "/job-api-srtime"

#: path supervisor registers to receive requests from server
SERVER_URI = "/job-api-request"

#: path supervisor registers to receive pings from server
SERVER_PING_URI = "/job-api-ping"

#: path supervisor registers to receive requests from job_process for file PUTs
DATA_FILE_URI = "/job-cmd-data-file"

#: path supervisor registers to receive requests from job_process for global resources
GLOBAL_RESOURCES_URI = "/global-resources"

# POSIT: These are the same queues as in schema-common.common.enum.SbatchQueue
NERSC_QUEUES = frozenset(("debug", "premium", "realtime", "regular"))

#: where user data files come in (job_supervisor)
DATA_FILE_ROOT = None

#: path supervisor registers to receive requests from job_process for simulation file GETs/PUTs
SIM_DB_FILE_URI = "/sim-db-file"

#: how jobs request files (relative to `srdb.root`)
SUPERVISOR_SRV_SUBDIR = "supervisor-srv"

#: how jobs request files (absolute)
SUPERVISOR_SRV_ROOT = None

#: address where supervisor binds to
DEFAULT_IP = "127.0.0.1"

#: port supervisor listens on
DEFAULT_PORT = 8001

#: _cfg declaration for supervisor_uri for drivers
DEFAULT_SUPERVISOR_URI_DECL = (
    "http://{}:{}".format(DEFAULT_IP, sirepo.const.PORT_DEFAULTS.supervisor),
    str,
    "how to reach supervisor",
)

#: status values
CANCELED = "canceled"
COMPLETED = "completed"
ERROR = "error"
JOB_RUN_PURGED = "job_run_purged"
MISSING = "missing"
PENDING = "pending"
RUNNING = "running"
UNKNOWN = "unknown"

#: Queued or running
ACTIVE_STATUSES = frozenset((PENDING, RUNNING))

#: When the job is inactive
EXIT_STATUSES = frozenset((CANCELED, COMPLETED, ERROR, MISSING, JOB_RUN_PURGED))

#: Valid values for job status
STATUSES = EXIT_STATUSES.union(ACTIVE_STATUSES)

#: For communication between job_agent and job_cmd
JOB_CMD_STATE_SBATCH_RUN_STATUS_STOP = "sbatch_run_status_stop"
JOB_CMD_STATE_EXITS = EXIT_STATUSES.union((JOB_CMD_STATE_SBATCH_RUN_STATUS_STOP,))

#: job_cmds
CMD_COMPUTE = "compute"
CMD_DOWNLOAD_RUN_FILE = "download_run_file"
CMD_SBATCH_RUN_STATUS = "sbatch_run_status"

#: jobRunMode and kinds; should come from schema
SEQUENTIAL = "sequential"
PARALLEL = "parallel"
SBATCH = "sbatch"

#: valid jobRunMode values
RUN_MODES = frozenset((SEQUENTIAL, PARALLEL, SBATCH))

#: categories of jobs
KINDS = frozenset((SEQUENTIAL, PARALLEL))

# https://docs.nersc.gov/jobs/policy/
# https://docs.nersc.gov/performance/knl/getting-started/#knl-vs-haswell
#: Max values for each nersc queue
NERSC_QUEUE_MAX = PKDict(
    hours=PKDict(
        debug=0.5,
        premium=48,
        regular=48,
    ),
    cores=PKDict(
        debug=34816,
        premium=56704,
        regular=61824,
    ),
)


_QUASI_SID_PREFIX = "_1_"

#: Allow sids for different kinds of jobs (not simulations)
QUASI_SID_RE = re.compile(f"^{_QUASI_SID_PREFIX}")

#: Must match length of simulation_db._ID_LEN
_QUASI_SID_OP_KEY_LEN = 5


_cfg = None


#: use to separate components of job_id
_JOB_ID_SEP = "-"


def agent_cmd_stdin_env(cmd, env, uid, cwd=".", source_bashrc=""):
    """Convert `cmd` with `env` to script and cmd

    Uses tempfile so the file can be closed after the subprocess
    gets the handle. You have to close `stdin` after calling
    `tornado.process.Subprocess`, which calls `subprocess.Popen`
    inline, since it' not ``async``.

    Args:
        cmd (iter): list of words to be quoted
        env (str): empty or result of `agent_env`
        uid (str): which user should be logged in
        cwd (str): directory for the agent to run in (will be created if it doesn't exist)

    Returns:
        tuple: new cmd (tuple), stdin (file), env (PKDict or None)
    """
    import os
    import tempfile

    if sirepo.feature_config.cfg().trust_sh_env:
        source_bashrc = ""
    t = tempfile.TemporaryFile()
    c = "exec " + " ".join(("'{}'".format(x) for x in cmd))
    # POSIT: we control all these values
    t.write(
        """{}
set -e
mkdir -p '{}'
cd '{}'
{}
{}
""".format(
            source_bashrc,
            cwd,
            cwd,
            env or agent_env(uid=uid),
            c,
        ).encode()
    )
    t.seek(0)
    if sirepo.feature_config.cfg().trust_sh_env:
        # Trust the local environment
        return ("bash", t, None)
    # it's reasonable to hardwire this path, even though we don't
    # do that with others. We want to make sure the subprocess starts
    # with a clean environment (no $PATH). You have to pass HOME.
    return ("/bin/bash", "-l"), t, PKDict(HOME=os.environ["HOME"])


def agent_env(uid, env=None):
    """Convert to bash environment

    Args:
        uid (str): which user is running this agent process
        env (str): empty or base environment

    Returns:
        str: bash environment ``export`` commands
    """
    x = pkconfig.to_environ(
        (
            "pykern.*",
            "sirepo.feature_config.*",
        ),
        exclude_re=pykern.pkdebug.SECRETS_RE,
    )
    env = (
        (env or PKDict())
        .pksetdefault(
            **x,
        )
        .pksetdefault(
            PYTHONUNBUFFERED="1",
            SIREPO_AUTH_LOGGED_IN_USER=uid,
            SIREPO_JOB_MAX_MESSAGE_BYTES=_cfg.max_message_bytes,
            SIREPO_JOB_PING_INTERVAL_SECS=_cfg.ping_interval_secs,
            SIREPO_JOB_PING_TIMEOUT_SECS=_cfg.ping_timeout_secs,
            SIREPO_JOB_VERIFY_TLS=_cfg.verify_tls,
            SIREPO_SIMULATION_DB_LOGGED_IN_USER=uid,
            SIREPO_SRDB_ROOT=lambda: sirepo.srdb.root(),
        )
    )
    if not sirepo.feature_config.cfg().trust_sh_env:
        env.pksetdefault(
            PYTHONPATH="",
            PYTHONSTARTUP="",
        )
    for k in env.keys():
        assert not pykern.pkdebug.SECRETS_RE.search(
            k
        ), "unexpected secret key={} match={}".format(
            k,
            pykern.pkdebug.SECRETS_RE,
        )
    return "\n".join(("export {}='{}'".format(k, v) for k, v in env.items()))


def cfg():
    return _cfg or init_module()


def init_module():
    global _cfg

    if _cfg:
        return _cfg
    _cfg = pkconfig.init(
        max_message_bytes=(
            int(2e8),
            pkconfig.parse_bytes,
            "maximum message size throughout system",
        ),
        ping_interval_secs=(
            2 * 60,
            pkconfig.parse_seconds,
            "how long to wait between sending keep alive pings",
        ),
        ping_timeout_secs=(
            4 * 60,
            pkconfig.parse_seconds,
            "how long to wait for a ping response",
        ),
        server_secret=(
            "a very secret, secret",
            str,
            "shared secret between supervisor and server",
        ),
        verify_tls=(
            not pkconfig.channel_in("dev"),
            bool,
            "do not validate (self-signed) certs",
        ),
    )
    global SUPERVISOR_SRV_ROOT, DATA_FILE_ROOT

    SUPERVISOR_SRV_ROOT = sirepo.srdb.root().join(SUPERVISOR_SRV_SUBDIR)
    DATA_FILE_ROOT = SUPERVISOR_SRV_ROOT.join(DATA_FILE_URI[1:])
    return _cfg


def is_ok_reply(value):
    if not isinstance(value, PKDict):
        return False
    return value == _OK_REPLY or value.get("state") == COMPLETED


def join_jid(uid, sid, compute_model):
    """A Job is a tuple of user, sid, and compute_model.

    A jid is words and dashes.

    Args:
        uid (str): user id
        sid (str): simulation id
        compute_model (str): model name
    Returns:
        str: unique name (treat opaquely)
    """
    return _JOB_ID_SEP.join((uid, sid, compute_model))


def ok_reply():
    return _OK_REPLY.copy()


def quasi_jid(uid, op_key, method):
    """Creates an id for a non-simulation job

    Args:
        uid (str): user id
        op_key (str): "stful" or "stlss"
        method (str): statelessCompute or statefulCompute method
    """
    assert len(op_key) == _QUASI_SID_OP_KEY_LEN
    return join_jid(uid, _QUASI_SID_PREFIX + op_key, method)


def sbatch_login_ok():
    """Response for sbatchLogin API

    Returns:
        PKDict: success response
    """
    return PKDict(loginSuccess=True)


def split_jid(jid):
    """Split jid into named parts

    Args:
        jid (str): properly formed job identifier
    Returns:
        PKDict: parts named uid, sid, compute_model.
    """
    return PKDict(
        pykern.pkcompat.zip_strict(
            ("uid", "sid", "compute_model"),
            jid.split(_JOB_ID_SEP),
        )
    )


def supervisor_file_uri(supervisor_uri, *args):
    # trailing slash necessary
    return "{}{}/".format(supervisor_uri, "/".join(args))
