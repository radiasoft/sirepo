#!/bin/bash
set -eou pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

declare _mail_d=~/mail

_env_common() {
    export PYKERN_PKDEBUG_WANT_PID_TIME=1
}

_env_mail_common() {
    export SIREPO_SMTP_FROM_NAME=DevSupport
    export SIREPO_SMTP_FROM_EMAIL=$USER+support@localhost.localdomain
    if [[ ! ${SIREPO_AUTH_METHODS:-} =~ email ]]; then
        export SIREPO_AUTH_METHODS=email:guest
    fi
}

_env_mail_smtp() {
    _env_mail_common
    export SIREPO_SMTP_FROM_EMAIL=$USER+support@localhost.localdomainn
    export SIREPO_SMTP_SEND_DIRECTLY=1
    export SIREPO_SMTP_SERVER=localhost
}

_env_moderate() {
    declare sim_type=$1
    export SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES=$sim_type
    export SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL=$USER+moderator@localhost.localdomain
    _msg "Moderated sim_type=$sim_type"
    _setup_smtp
    _env_common
}

_err() {
    _msg "$@"
    return 1
}

_exec_all() {
    _env_common
    exec sirepo service http
}

_main() {
    declare mode=${1:-missing-arg}
    shift || true
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

_op_bluesky() {
    export SIREPO_AUTH_BLUESKY_SECRET=bluesky-secret
    export SIREPO_AUTH_METHODS=email:bluesky
    _msg "To test, you need a sim, but this is the structure:

curl -H 'Content-Type: application/json' -D - -X POST http://localhost:8000/auth-bluesky-login -d '{\"simulationId\": \"kRfyDC2q\", \"simulationType\": \"srw\"}'
"
    _op_mail
}

_op_flash() {
    export SIREPO_FEATURE_CONFIG_PROPRIETARY_OAUTH_SIM_TYPES=flash
    export SIREPO_SIM_OAUTH_FLASH_INFO_VALID_USER=G
    if [[ ! ${SIREPO_SIM_OAUTH_FLASH_KEY:-} || ! ${SIREPO_SIM_OAUTH_FLASH_SECRET:-} ]]; then
        echo 'You must set $SIREPO_SIM_OAUTH_FLASH_KEY and $SIREPO_SIM_OAUTH_FLASH_SECRET' 1>&2
        exit 1
    fi
    _exec_all
}

_op_jupyterhub() {
    # POSIT: versions same in container-beamsim-jupyter/build.sh
    # Order is important: jupyterlab-server should be last so it isn't
    # overwritten with a newer version.
    declare p=$(pip freeze)
    declare -a i=()
    declare f
    for f in \
        jupyterhub==1.4.2 \
        jupyterlab==3.1.14  \
        notebook==6.5.4 \
        jupyterlab-server==2.8.2\
        ; do
        if ! [[ $p =~ $f ]]; then
            i+=( $f )
        fi
    done
    if (( ${#i[@]} > 0 )); then
        pip install "${i[@]}"
    fi
    if ! type configurable-http-proxy &> /dev/null; then
        npm install --global configurable-http-proxy
    fi
    _env_moderate jupyterhublogin
    sirepo service tornado &
    sirepo service nginx-proxy &
    sirepo job_supervisor &
    sirepo service jupyterhub &
    declare -a x=( $(jobs -p) )
    # TERM is better than KILL
    trap "kill ${x[*]}" EXIT
    wait -n
}

_op_ldap() {
    if ! systemctl is-active slapd &> /dev/null; then
       _msg "setting up ldap/slapd"
       bash setup-ldap.sh
    fi
    export SIREPO_AUTH_METHODS=guest:ldap
    _msg 'To test:

Login as vagrant@radiasoft.net/vagrant
'
    _exec_all
}


_op_mail() {
    _setup_smtp
    _exec_all
}

_op_moderate() {
    _env_moderate srw
    _exec_all
}

_op_no_smtp_mail() {
    # POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
    export SIREPO_SMTP_SERVER=dev
    _env_mail_common
    _exec_all
}

_op_server_status() {
    declare u=$(cd "$(dirname "$0")"/../run/user && ls -d ???????? 2>/dev/null | head -1)
    if [[ ! $u ]]; then
        _err 'Start the server first to create a user and then server_status can work'
    fi
    export SIREPO_AUTH_BASIC_PASSWORD=password
    export SIREPO_AUTH_BASIC_UID=$u
    export SIREPO_AUTH_METHODS=guest:basic
    export SIREPO_FEATURE_CONFIG_API_MODULES=status
    _msg "To test:

curl -u '$u:$SIREPO_AUTH_BASIC_PASSWORD' http://localhost:8000/server-status
"
    _exec_all
}

_op_test_mail() {
    _msg 'Testing local mail delivery'
    rm -f "$_mail_d"/[0-9]*
    echo xyzzy | sendmail "$USER"@localhost.localdomain
    declare i
    for i in $(seq 4); do
        sleep 1
        if grep -s xyzzy "$_mail_d"/1 &>/dev/null; then
            rm "$_mail_d"/1
            return
        fi
    done
    _err mail delivery test failed
}

_setup_smtp() {
    _env_mail_smtp
    if [[ ! -d $_mail_d ]]; then
        install -m 700 -d "$_mail_d"
    fi
    if [[ ! -r ~/.procmailrc ]]; then
        install -m 600 /dev/stdin ~/.procmailrc <<'END'
UMASK=077
:0
mail/.
END
    fi
    declare f
    for f in postfix procmail; do
        if ! rpm -q "$f" &> /dev/null; then
            _msg "installing $f"
            sudo dnf install -y -q "$f"
        fi
    done
    if [[ ! $(postconf -n recipient_delimiter) ]]; then
        _msg 'configuring postfix'
        sudo su - <<'END'
        postconf -e \
            inet_protocols=ipv4 \
            mailbox_command=/usr/bin/procmail \
            'mydestination=$myhostname, localhost.$mydomain, localhost, localhost.localdomain' \
            recipient_delimiter=+
        systemctl enable postfix
        systemctl restart postfix
END
        _op_test_mail
    fi
}

_main "$@"
