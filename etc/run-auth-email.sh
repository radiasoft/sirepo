#!/bin/bash
# see run-jupyterhub.sh for setting up local mail delivery
export SIREPO_FROM_EMAIL='support@radiasoft.net'
export SIREPO_FROM_NAME='RadiaSoft Support'
export SIREPO_SMTP_PASSWORD='vagrant'
# POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
export SIREPO_SMTP_SERVER='dev'
export SIREPO_SMTP_USER='vagrant'
export SIREPO_AUTH_METHODS='email:guest'
export PYKERN_PKDEBUG_WANT_PID_TIME=1
exec sirepo service http
