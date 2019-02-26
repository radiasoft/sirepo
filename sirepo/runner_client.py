import aenum
import contextlib
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import srdb
import socket


_CHUNK_SIZE = 4096


class JobStatus(aenum.Enum):
    MISSING = 'missing'     # no data on disk, not currently running
    RUNNING = 'running'     # data on disk is incomplete but it's running
    ERROR = 'error'         # data on disk exists, but job failed somehow
    CANCELED = 'canceled'   # data on disk exists, but is incomplete
    COMPLETED = 'completed' # data on disk exists, and is fully usable


def _rpc(request):
    """Send an RPC message to the runner daemon, and get the response.

    Args:
        request: the request, as a json-encodeable object

    Returns:
        response: the server response
    """
    request_bytes = pkjson.dump_bytes(request)
    with contextlib.closing(socket.socket(socket.AF_UNIX)) as sock:
        sock.connect(str(srdb.runner_socket_path()))
        # send the request
        sock.sendall(request_bytes)
        # send EOF, so the other side knows we've sent the whole thing
        sock.shutdown(socket.SHUT_WR)
        # read the response
        response_bytes = bytearray()
        while True:
            chunk = sock.recv(_CHUNK_SIZE)
            if not chunk:
                break
            response_bytes += chunk
    if response_bytes == b'':
        raise AssertionError('runner daemon had an unknown error')
    return pkjson.load_any(bytes(response_bytes))


def start_job(run_dir, jhash, cmd):
    return _rpc({
        'action': 'start_job',
        'run_dir': str(run_dir),
        'jhash': jhash,
        'cmd': cmd,
    })


def job_status(run_dir, jhash):
    result = _rpc({
        'action': 'job_status', 'run_dir': str(run_dir), 'jhash': jhash,
    })
    return JobStatus(result.status)


def cancel_job(run_dir, jhash):
    return _rpc({
        'action': 'cancel_job', 'run_dir': str(run_dir), 'jhash': jhash,
    })
