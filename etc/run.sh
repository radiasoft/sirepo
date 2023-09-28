#!/bin/bash
#source ~/.bashrc
set -eou pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

_env_common() {
    export PYKERN_PKDEBUG_WANT_PID_TIME=1
}

_env_email_common() {
    # default is fine
    unset SIREPO_FROM_EMAIL
    unset SIREPO_FROM_NAME
    export SIREPO_AUTH_METHODS='email:guest'
}

_env_email_smtp() {
    _env_email_common
    export SIREPO_SMTP_FROM_EMAIL=$USER+support@localhost.localdomainn
    export SIREPO_SMTP_SEND_DIRECTLY=1
    export SIREPO_SMTP_SERVER=localhost
}

_err() {
    _msg "$@"
    return 1
}

_main() {
    declare mode=${1:-missing-arg}
    shift
    declare f=_op_$mode
    if [[ $(type -t "$f") != 'function' ]]; then
        _err "invalid mode=$mode
usage: bash ${BASH_SOURCE[0]} mode
where mode is one of:
$(compgen -A function _op_ | sed -e 's/^_op_//')"
    fi
    "$f" "$@"
}

_msg() {
    echo "$@" 1>&2
}

_op_moderate() {
    export SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES=srw
    export SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL=$SIREPO_FROM_EMAIL
    _msg "Moderated sym_type=$SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES"
    _setup_smtp
    _exec_all
}

_op_email() {
    _setup_smtp
    _exec_all
}

_op_no_smtp_email() {
    # POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
    export SIREPO_SMTP_SERVER=dev
    _env_email_common
    _exec_all
}

_exec_all() {
    _env_common
    exec sirepo service http
}

_setup_smtp() {
    _env_smtp_email
    if [[ -d ~/mail ]]; then
        return
    fi
    echo 'Setting up SMTP (one time, takes a few minutes)' 1>&2
    install -m 700 -d ~/mail
    install -m 600 /dev/stdin ~/.procmailrc <<'END'
UMASK=077
:0
mail/.
END
    sudo su - <<'END'
        dnf install -y postfix procmail
        # Necessary or on docker on Ubuntu tries to open ipv6
        sed -i '/^::1\s/d' /etc/hosts
        postconf -e \
            'mydestination=$myhostname, localhost.$mydomain, localhost, localhost.localdomain' \
            mailbox_command=/usr/bin/procmail \
            recipient_delimiter=+
        systemctl enable postfix
        systemctl restart postfix
END
    _msg 'Testing local mail delivery'
    echo xyzzy | sendmail vagrant@localhost.localdomain
    sleep 4
    if ! grep -s xyzzy ~/mail/1; then
        _err mail delivery test failed
    fi
    rm ~/mail/1
}

_main "$@"
