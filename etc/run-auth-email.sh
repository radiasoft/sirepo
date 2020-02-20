#!/bin/bash
export SIREPO_AUTH_EMAIL_FROM_EMAIL='support@radiasoft.net'
export SIREPO_AUTH_EMAIL_FROM_NAME='RadiaSoft Support'
export SIREPO_AUTH_EMAIL_SMTP_PASSWORD='n/a'
# POSIT: same as sirepo.auth.email._DEV_SMTP_SERVER
export SIREPO_AUTH_EMAIL_SMTP_SERVER='dev'
export SIREPO_AUTH_EMAIL_SMTP_USER='n/a'
export SIREPO_AUTH_METHODS='email:guest'
export PYKERN_PKDEBUG_WANT_PID_TIME=1
exec sirepo service http
