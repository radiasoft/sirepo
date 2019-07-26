#!/bin/bash
#
# Start sirepo with "tini"
#
. ~/.bashrc
set -euo pipefail
cd '{sirepo_db_dir}'
export PYKERN_PKCONFIG_CHANNEL=alpha
export PYTHONUNBUFFERED=1
export SIREPO_PKCLI_SERVICE_PORT='{sirepo_port}'
export SIREPO_PKCLI_SERVICE_RUN_DIR="$PWD"
export SIREPO_SERVER_DB_DIR="$PWD/db"
export SIREPO_COOKIE_IS_SECURE=false
mkdir -m 700 -p "$SIREPO_SERVER_DB_DIR"
f=$SIREPO_SERVER_DB_DIR/cookie_private_key
if [[ ! -r $f ]]; then
    sirepo auth gen_private_key > "$f"
fi
export SIREPO_COOKIE_PRIVATE_KEY=$(cat "$f")
exec sirepo service http
