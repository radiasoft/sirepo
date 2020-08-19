#!/bin/bash
: how to setup postfix with sasl for smtpd auth <<'EOF'
# as user vagrant
install -m 600 /dev/stdin ~/.procmailrc <<'END'
UMASK=077
:0
mail/.
END
install -m 600 -d ~/mail
sudo su -
dnf install -y postfix cyrus-sasl cyrus-sasl-lib cyrus-sasl-plain telnet procmail
systemctl start postfix
systemctl enable postfix
echo vagrant | saslpasswd2 -f /etc/sasldb2 -c -p vagrant
chgrp mail /etc/sasldb2
cat > /etc/sasl2/smtpd-sasldb.conf <<'END'
auxprop_plugin: sasldb
log_level: 4
mech_list: plain
pwcheck_method: auxprop
END
postconf smtpd_sasl_path=smtpd-sasldb smtpd_sasl_auth_enable=yes 'mailbox_command=/usr/bin/procmail -a "$EXTENSION"'
systemctl restart postfix
exit
# to test procmail delivery
echo hello | sendmail vagrant
# to test sasl
(sleep 1; echo EHLO localhost; sleep 1; echo AUTH PLAIN AHZhZ3JhbnQAdmFncmFudA==; sleep 1; echo QUIT) | telnet localhost 25
# then use
export SIREPO_SMTP_SERVER='localhost'
EOF
export SIREPO_FROM_EMAIL='support@radiasoft.net'
export SIREPO_FROM_NAME='RadiaSoft Support'
export SIREPO_SMTP_PASSWORD='vagrant'
# POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
export SIREPO_SMTP_SERVER='dev'
export SIREPO_SMTP_USER='vagrant'
export SIREPO_AUTH_METHODS='email:guest'
export PYKERN_PKDEBUG_WANT_PID_TIME=1
exec sirepo service http
