#!/bin/bash
set -eou pipefail
# See run-auth-moderate.sh for using local mail delivery.
# This echo's the URL to the logs (SIREPO_SMTP_SERVER=dev)
export SIREPO_AUTH_BLUESKY_SECRET=bluesky-secret
export SIREPO_AUTH_METHODS=email:bluesky
export SIREPO_FROM_EMAIL=support@radiasoft.net
export SIREPO_FROM_NAME='RadiaSoft Support'
export SIREPO_SMTP_PASSWORD=vagrant
# POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
export SIREPO_SMTP_SERVER=dev
export SIREPO_SMTP_USER=vagrant
cat <<EOF
To test, you need a simulation:

curl -H 'Content-Type: application/json' -D - -X POST http://localhost:8000/auth-bluesky-login -d '{"simulationId": "kRfyDC2q", "simulationType": "srw"}'

EOF
exec sirepo service http
