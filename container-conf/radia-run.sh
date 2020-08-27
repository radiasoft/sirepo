#!/bin/bash
#
# Docker CMD to start Sirepo in development mode.
#
# DO NOT USE on a public server or in an environment with multiple users.
#
source ~/.bashrc
set -euo pipefail
cd '{sirepo_db_dir}'
export PYKERN_PKCONFIG_CHANNEL=dev
export PYTHONUNBUFFERED=1
export SIREPO_JOB_SERVER_SECRET=$RANDOM$RANDOM$RANDOM$RANDOM
export SIREPO_PKCLI_JOB_SUPERVISOR_DEBUG=false
export SIREPO_PKCLI_SERVICE_PORT='{sirepo_port}'
export SIREPO_PKCLI_SERVICE_RUN_DIR="$PWD"
export SIREPO_PKCLI_SERVICE_USE_RELOADER=false
export SIREPO_SRDB_ROOT="$PWD/db"
mkdir -m 700 -p "$SIREPO_SRDB_ROOT"
# so user stays logged in on restarts; especially important with guest logins
f=$SIREPO_SRDB_ROOT/cookie_private_key
if [[ ! -r $f ]]; then
    sirepo auth gen_private_key > "$f"
fi
export SIREPO_COOKIE_PRIVATE_KEY=$(cat "$f")
exec sirepo service http
