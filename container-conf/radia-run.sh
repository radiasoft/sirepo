#!/bin/bash
#
# Start sirepo
#
. ~/.bashrc
set -euo pipefail
cd '{sirepo_db_dir}'
export PYKERN_PKCONFIG_CHANNEL=alpha
export PYTHONUNBUFFERED=1
export SIREPO_PKCLI_SERVICE_PORT='{sirepo_port}'
export SIREPO_PKCLI_SERVICE_RUN_DIR="$PWD"
export SIREPO_SRDB_ROOT="$PWD/db"
export SIREPO_COOKIE_IS_SECURE=false
mkdir -m 700 -p "$SIREPO_SRDB_ROOT"
f=$SIREPO_SRDB_ROOT/cookie_private_key
if [[ ! -r $f ]]; then
    sirepo auth gen_private_key > "$f"
fi
export SIREPO_COOKIE_PRIVATE_KEY=$(cat "$f")
exec sirepo service http
