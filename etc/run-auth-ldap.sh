#!/bin/bash
# see run-jupyterhub.sh for setting up local mail delivery
export SIREPO_FROM_EMAIL='support@radiasoft.net'
export SIREPO_FROM_NAME='RadiaSoft Support'
export SIREPO_SMTP_PASSWORD='vagrant'
# POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
export SIREPO_SMTP_SERVER='dev'
export SIREPO_SMTP_USER='vagrant'
export SIREPO_AUTH_METHODS='email:guest:ldap'
export PYKERN_PKDEBUG_WANT_PID_TIME=1

# primary cause of failed wheel generation
exec pip install --upgrade pip

# install prerequisites
exec yum groupinstall "Development tools"
exec yum install openldap-devel python-devel

# secondary cause of failed wheel generation
exec pip install --upgrade setuptools wheel

# main installs
exec pip install python-ldap
exec yum -y install openldap-clients openldap-servers

# create user
exec sudo ldapadd -f vagrant_user.ldif -x -D cn=admin,dc=example,dc=com -w supersecret

exec sirepo service http
