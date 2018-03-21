#!/bin/bash
#
# Start sirepo with "tini"
#
. ~/.bashrc
set -e
cd '{sirepo_db_dir}'
export PYKERN_PKCONFIG_CHANNEL=alpha
export PYTHONUNBUFFERED=1
export SIREPO_PKCLI_SERVICE_PORT='{sirepo_port}'
export SIREPO_PKCLI_SERVICE_RUN_DIR="$PWD"
export SIREPO_SERVER_DB_DIR="$PWD/db"
exec sirepo service http
