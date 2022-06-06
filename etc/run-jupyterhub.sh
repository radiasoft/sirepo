#!/bin/bash
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

if [[ ! ${SIREPO_AUTH_METHODS:-} ]]; then
    export SIREPO_AUTH_METHODS=email
elif [[ ! $SIREPO_AUTH_METHODS =~ 'email' ]]; then
    export SIREPO_AUTH_METHODS=$SIREPO_AUTH_METHODS:email
fi

if [[ ${SIREPO_AUTH_GITHUB_KEY:-} || ${SIREPO_AUTH_GITHUB_SECRET:-} ]]; then
    export SIREPO_AUTH_GITHUB_METHOD_VISIBLE=0
    export SIREPO_AUTH_METHODS="$SIREPO_AUTH_METHODS:github"
    export SIREPO_SIM_API_JUPYTERHUBLOGIN_RS_JUPYTER_MIGRATE=1
fi

sirepo service nginx-proxy &
sirepo service uwsgi &
sirepo job_supervisor &
sirepo service jupyterhub &
if ! wait -n; then
    kill -9 $(jobs -p) || true
    exit 1
fi
