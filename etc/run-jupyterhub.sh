#!/bin/bash
set -eou pipefail

export SIREPO_AUTH_METHODS=email
export SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES=jupyterhublogin

if [[ ${SIREPO_AUTH_GITHUB_KEY:-} || ${SIREPO_AUTH_GITHUB_SECRET:-} ]]; then
    export SIREPO_AUTH_GITHUB_METHOD_VISIBLE=0
    export SIREPO_AUTH_METHODS="$SIREPO_AUTH_METHODS:github"
    export SIREPO_SIM_API_JUPYTERHUBLOGIN_RS_JUPYTER_MIGRATE=1
fi

sirepo service nginx-proxy &
sirepo service uwsgi &
sirepo job_supervisor &
sirepo service jupyterhub &
if ! wait -n; then
    kill -9 $(jobs -p) || true
    exit 1
fi
