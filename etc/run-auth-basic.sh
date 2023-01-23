#!/bin/bash
set -eou pipefail
# go to the run directory
_uid=$(cd "$(dirname "$0")"/../run/user && ls -d ???????? | head -1)
echo "using uid=$_uid"
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_AUTH_BASIC_PASSWORD=password
export SIREPO_AUTH_BASIC_UID=$_uid
export SIREPO_AUTH_METHODS=email:basic
export SIREPO_FEATURE_CONFIG_API_MODULES=status
cat <<EOF
To test:

curl -u "$_uid:$SIREPO_AUTH_BASIC_PASSWORD" http://localhost:8000/server-status

EOF
exec sirepo service http
