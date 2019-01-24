import json
import socket

# XX TODO: fill in
# https://github.com/radiasoft/sirepo/issues/1499
_db_dir = XXX


class RunnerError(Exception):
    pass


def _rpc(request):
    """Send an RPC message to the runner daemon, and get the response.

    Args:
        request: the request, as a json-encodeable object

    Returns:
        response: the server response
    """
    request_bytes = json.dumps(request).encode('ascii')
    with socket.socket(socket.AF_UNIX) as sock:
        sock.connect(_db_dir.join('runner.sock'))
        sock.sendall(request_bytes)
        sock.shutdown(socket.SHUT_WR)
        response_bytes = bytearray()
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_bytes += chunk
    response = json.loads(response_bytes)
    if 'error_string' in response:
        raise RunnerError(response['error_string'])
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
