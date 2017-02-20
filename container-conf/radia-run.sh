#!/bin/bash
#
# Start sirepo with "tini"
#
. ~/.bashrc
set -e
cd '{sirepo_db_dir}'
export SIREPO_PKCLI_SERVICE_PORT={sirepo_port}
export SIREPO_PKCLI_SERVICE_DB_DIR=$PWD
export PYTHONUNBUFFERED=1
exec sirepo service http
