#!/bin/bash
#
# Start Sirepo Jupyterhub with email login
# If $SIREPO_AUTH_GITHUB_KEY and $SIREPO_AUTH_GITHUB_SECRET, then
# add github authentication to test SIREPO_SIM_API_JUPYTERHUBLOGIN_RS_JUPYTER_MIGRATE.

#
# juptyerhub upgrades: If you get this:
# Found database schema version 4dc2d5a8c53c != 651f5419b74d. Backup your database and run `jupyterhub upgrade-db` to upgrade to the latest schema.
# Then you need to:
#   cd run/jupyterhub
#   jupyterhub upgrade-db
# so that it sees the sqlite db.
set -eou pipefail

if [[ ! -d ~/mail ]]; then
    install -m 700 -d ~/mail
    install -m 600 /dev/stdin ~/.procmailrc <<'END'
UMASK=077
:0
mail/.
END
    sudo su - <<'END'
        dnf install -y postfix procmail
        postconf -e \
            'mydestination=$myhostname, localhost.$mydomain, localhost, localhost.localdomain' \
            mailbox_command=/usr/bin/procmail
        systemctl enable postfix
        systemctl restart postfix
END
    echo 'Testing mail delivery'
    echo hello | sendmail vagrant@localhost.localdomain
    sleep 4
    if ! grep -s hello ~/mail/1; then
        echo mail delivery test failed
        exit 1
    fi
    rm ~/mail/1
fi

export SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES=jupyterhublogin
export SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL='vagrant@localhost.localdomain'
export SIREPO_FROM_EMAIL='$USER+support@localhost.localdomain'
export SIREPO_FROM_NAME='RadiaSoft Support'
export SIREPO_SMTP_SERVER='localhost'
export SIREPO_SMTP_SEND_DIRECTLY=1

export SIREPO_AUTH_METHODS=${SIREPO_AUTH_METHODS:+$SIREPO_AUTH_METHODS:}email
if [[ ${SIREPO_AUTH_GITHUB_KEY:-} && ${SIREPO_AUTH_GITHUB_SECRET:-} ]]; then
    export SIREPO_AUTH_METHODS=$SIREPO_AUTH_METHODS:github
    export SIREPO_AUTH_GITHUB_METHOD_VISIBLE=0
    export SIREPO_SIM_API_JUPYTERHUBLOGIN_RS_JUPYTER_MIGRATE=1
fi

sirepo service tornado &
sirepo service nginx-proxy &
sirepo job_supervisor &
sirepo service jupyterhub &
declare -a x=( $(jobs -p) )
# this doesn't kill uwsgi for some reason; TERM is better than KILL
trap "kill ${x[*]}" EXIT
wait -n
