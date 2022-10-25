#!/bin/bash
set -eou pipefail
cd "$(dirname "$0")"/..
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_JOB_DRIVER_MODULES=local
export SIREPO_MPI_CORES=2
export PORT=3000 npm start
export SIREPO_REACT_PROXY_URI=http://127.0.0.1:$PORT/
export SIREPO_PKCLI_JOB_SUPERVISOR_IP=0.0.0.0
export NO_COLOR=true
cd react
if [[ ! -d node_modules ]]; then
    npm install
fi

_kill() {
    declare pid=$1
    declare p
    for p in $(ps -o pid= --ppid "$pid"); do
        _kill "$pid"
    done
    echo "KILL $pid"
    kill -9 "$pid" >& /dev/null || true
}

TERM=dumb NO_COLOR=true npm start &
trap "_kill $!" EXIT
cd -
sirepo job_supervisor
