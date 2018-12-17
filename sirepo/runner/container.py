from sirepo import runner, simulation_db
from base64 import b64encode
from contextlib import contextmanager
from functools import partial
import logging
import json
import trio
import docker
import redis
import requests

__all__ = ["serve", "ContainerJob"]

# XX TODO: what's the right way to do logging in pykern/sirepo?
log = logging.getLogger(__name__)

# The redis key we use for the request list
REQUEST_LIST_KEY = "seq:job_queue"
# The redis key we use for the job status hash
JOB_STATUS_HASH_KEY = "hash:job_status"

# How often threaded blocking operations should wake up and check for Trio
# cancellation
CANCEL_POLL_INTERVAL = 1

# Global connection pools (don't worry, they don't actually make any
# connections until we start using them)
REDIS = redis.from_url("redis://localhost:6379/0")
DOCKER = docker.from_env()


def encode_request(request):
    return json.dumps(request).encode("utf-8")


def decode_request(request):
    return json.loads(request.decode("utf-8"))


def submit_request(request):
    print("submitting:", request)
    REDIS.rpush(REQUEST_LIST_KEY, encode_request(request))


# XX TODO: how to integrate this properly into pykern/sirepo's logging system?
@contextmanager
def catch_and_log_errors(exc_type, msg, *args, **kwargs):
    try:
        yield
    except exc_type as exc:
        log.exception(msg, *args, **kwargs)


# Helper to call redis blpop in a async/cancellation-friendly way
async def pop_encoded_request():
    while True:
        retval = await trio.run_sync_in_worker_thread(
            partial(
                REDIS.blpop, [REQUEST_LIST_KEY], timeout=CANCEL_POLL_INTERVAL
            )
        )
        if retval is not None:
            _, encoded_request = retval
            return encoded_request


# Helper to call docker wait in a async/cancellation-friendly way
async def container_wait(container):
    while True:
        try:
            return await trio.run_sync_in_worker_thread(
                partial(container.wait, timeout=CANCEL_POLL_INTERVAL)
            )
        # ReadTimeout is what the documentation says this raises.
        # ConnectionError is what it actually raises.
        # We'll catch both just to be safe.
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
            pass


# The core request handler
async def handle_request(encoded_request):
    with catch_and_log_errors(Exception, "error handling request %r", encoded_request):
        request = decode_request(encoded_request)
        if request["type"] == "start":
            jid = request["jid"]
            # XX TODO should we do any sanitization here? e.g. specifying
            # arbitrary volumes allows arbitrary access to the host. Maybe
            # that's fine though.
            image = request["image"]
            command = request["command"]
            working_dir = request["working_dir"]
            # format: {host path: {"bind": container path, "mode": "rw"}}
            volumes = request["volumes"]
            # Technically a blocking call, but redis is fast and local so we
            # can get away with it
            REDIS.hset(JOB_STATUS_HASH_KEY, jid, b"running")
            # Start the container
            container = await trio.run_sync_in_worker_thread(
                partial(
                    DOCKER.containers.run,
                    image,
                    command,
                    working_dir=working_dir,
                    volumes=volumes,
                    name=jid,
                    auto_remove=True,
                    detach=True,
                )
            )
            # Returns a dict like: {"Error": None, "StatusCode": 0}
            print(await container_wait(container))
            # Technically a blocking call
            REDIS.hset(JOB_STATUS_HASH_KEY, jid, b"finished")
        elif request["type"] == "cancel":
            jid = request["jid"]
            container = DOCKER.containers.get(jid)
            container.stop()
            # Doesn't update status, because that will happen automatically
            # when it actually stops...
        else:
            raise RuntimeError(f"unknown request type: {request['type']!r}")


async def main():
    async with trio.open_nursery() as nursery:
        while True:
            encoded_request = await pop_encoded_request()
            print("handling request:", encoded_request)
            nursery.start_soon(handle_request, encoded_request)


def serve():
    trio.run(main)


################################################################
# Sirepo integration bits
################################################################

class ContainerJob(runner.JobBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sent_start_request = False

    def _is_processing(self):
        if (self._sent_start_request
            and REDIS.hget(JOB_STATUS_HASH_KEY, self.jid) != b"finished"):
            return True
        return False

    def _kill(self):
        submit_request({"type": "cancel", "jid": self.jid})

    def _start(self):
        # XX TODO I suspect this is not the right place to do this but I don't
        # understand the status tracking flow yet.
        simulation_db.write_status('running', self.run_dir)
        # XX TODO: this is a temporary hack, to work around sirepo's habit of
        # hard-coding the host run_dir into the command line. Longer-term we
        # need to untangle this.
        cmd = list(self.cmd)
        for i in range(len(cmd)):
            if cmd[i] == self.run_dir:
                cmd[i] = "/job-dir"
        # XX TODO: this encoding thing is also a gnarly hack
        # (1) for prototyping we want to work with the existing docker image,
        # which requires we detour through bash to set up our environment,
        # (2) self.cmd is already in the structured form we want to ultimately
        # pass straight through to exec,
        # (3) this means we need some hack to smuggle the real command
        # through all the quoting layers.
        #
        # base64 is a blunt hammer, but it's easier than figuring out the
        # details of all the different quoting systems.
        encoded_cmd = b64encode(json.dumps(cmd).encode("utf-8"))
        encoded_cmd = encoded_cmd.replace(b"\n", b"").replace(b" ", b"")
        encoded_cmd = encoded_cmd.decode("ascii")
        image = "radiasoft/sirepo"
        docker_command = [
            "/home/vagrant/.radia-run/tini",
            "--",
            "/bin/bash",
            "-c",
            """
            . ~/.bashrc
            exec python3 -c 'import json, base64, os; cmd = json.loads(base64.b64decode("%s")); os.execvp(cmd[0], cmd)'
            """ % encoded_cmd,
        ]
        submit_request({
            "type": "start",
            "jid": self.jid,
            "image": image,
            "command": docker_command,
            "working_dir": "/job-dir",
            "volumes": {str(self.run_dir): {"bind": "/job-dir", "mode": "rw"}},
        })
        # XX TODO: This is a hack to avoid a race condition where
        # _is_processing would return False for a moment after we call this.
        # If we could wait for the scheduler daemon to acknowledge our request
        # before returning, this would be unnecessary.
        self._sent_start_request = True


def init_class(app, uwsgi):
    # XX TODO: what else should we do here? check if we can connect to redis
    # and the service is running?
    return ContainerJob
