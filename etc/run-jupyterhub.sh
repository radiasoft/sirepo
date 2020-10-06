#!/bin/bash
set -eou pipefail

export SIREPO_AUTH_METHODS='email'
export SIREPO_FEATURE_CONFIG_SIM_TYPES='jupyterhublogin:srw'

if [[ "${1:-}" ]]; then
    if [[ "$#" -ne 2 ]]; then
        echo 'Must supply no args or excatly 2 args (GitHub key and secret).'
        exit 1
    fi
    export SIREPO_AUTH_GITHUB_KEY='$1'
    export SIREPO_AUTH_GITHUB_METHOD_VISIBLE=''
    export SIREPO_AUTH_GITHUB_SECRET='$2'
    export SIREPO_AUTH_METHODS="$SIREPO_AUTH_METHODS:github"
    export SIREPO_SIM_API_JUPYTERHUBLOGIN_RS_JUPYTER_MIGRATE='1'
fi

sirepo service nginx-proxy &
sirepo service uwsgi &
sirepo job_supervisor &
sirepo service jupyterhub &

# If one of the procs fails on startup then we want to kill
# all others and exit.
# Need to sleep a bit to give the procs time time to fail
sleep 2
if [[ $(jobs | wc -l) -eq 4 ]]; then
    echo 'waiting'
    jobs | wc -l
    wait -n
fi

for p in $(jobs -p); do
    kill "$p" > /dev/null 2>&1
    # wait is a builtin so it can't be used with timeout.
    # Use tail instead.
    if ! timeout 2 tail --pid="$p" -f /dev/null; then
        kill -9 "$p" > /dev/null 2>&1
    fi
done
