#!/bin/bash
set -eou pipefail
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_AUTH_BLUESKY_SECRET=bluesky-secret
export SIREPO_AUTH_METHODS=email:bluesky
export SIREPO_FROM_EMAIL=$USER+support@localhost.localdomain
export SIREPO_FROM_NAME='RadiaSoft Support'
# POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
export SIREPO_SMTP_SERVER='dev'
export SIREPO_SMTP_SERVER=localhost
export SIREPO_SMTP_USER='vagrant'
cat <<EOF
To test, you need a sim, but this is the structure:

curl -H 'Content-Type: application/json' -D - -X POST http://localhost:8000/auth-bluesky-login -d '{"simulationId": "kRfyDC2q", "simulationType": "srw"}'

EOF
exec sirepo service http
