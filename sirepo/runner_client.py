from pykern import pkjson
from sirepo import srdb
import socket


_CHUNK_SIZE = 4096


def _rpc(request):
    """Send an RPC message to the runner daemon, and get the response.

    Args:
        request: the request, as a json-encodeable object

    Returns:
        response: the server response
    """
    request_bytes = pkjson.dump_bytes(request)
    with socket.socket(socket.AF_UNIX) as sock:
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
    response = pkjson.json_load_any(response_bytes)
    if 'error_string' in response:
        raise AssertionError(response.error_string)
    return response


def start_job(jid, run_dir, config):
    return _rpc({
        'action': 'start_job',
        'jid': jid,
        'run_dir': run_dir,
        'config': config,
    })


def job_status(jid):
    return _rpc({'action': 'job_status', 'jid': jid})


def cancel_job(jid):
    return _rpc({'action': 'cancel_job', 'jid': jid})
