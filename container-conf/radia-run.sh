#!/bin/bash
#
# OCI CMD to start Sirepo in development mode.
#
# DO NOT USE on a public server or in an environment with multiple users.
#
source ~/.bashrc
set -euo pipefail
cd '{sirepo_db_dir}'
export PYKERN_PKCONFIG_CHANNEL=dev
export PYKERN_PKCONFIG_DEV_MODE=1
export PYTHONUNBUFFERED=1
export SIREPO_FEATURE_CONFIG_DEBUG_MODE=0
export SIREPO_JOB_SERVER_SECRET=$RANDOM$RANDOM$RANDOM$RANDOM
export SIREPO_PKCLI_JOB_AGENT_DEV_SOURCE_DIRS=0
export SIREPO_PKCLI_JOB_SUPERVISOR_USE_RELOADER=0
export SIREPO_PKCLI_SERVICE_PORT='{sirepo_port}'
export SIREPO_PKCLI_SERVICE_RUN_DIR="$PWD"
export SIREPO_PKCLI_SERVICE_USE_RELOADER=false
export SIREPO_SIMULATION_DB_DEV_VERSION=0
export SIREPO_SRDB_ROOT="$PWD/db"
export SIREPO_UTIL_CREATE_TOKEN_SECRET=
mkdir -m 700 -p "$SIREPO_SRDB_ROOT"
# so user stays logged in on restarts; especially important with guest logins
f=$SIREPO_SRDB_ROOT/cookie_private_key
if [[ ! -r $f ]]; then
    sirepo auth gen_private_key > "$f"
fi
export SIREPO_COOKIE_PRIVATE_KEY=$(cat "$f")
exec sirepo service http
