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
pip install --upgrade pip
echo "upgraded pip"

# install prerequisites
sudo yum groupinstall "Development tools"
sudo yum install openldap-devel python-devel
echo "installed prerequisites"

# secondary cause of failed wheel generation
pip install --upgrade setuptools wheel
echo "installed wheel setup"

# main installs
pip install python-ldap
sudo yum -y install openldap-clients openldap-servers
echo "installed ldap"

sudo systemctl start slapd
sudo systemctl enable slapd

cd /home/vagrant/src/radiasoft/sirepo
pip install -e .

"""

# assign default root and appended distunguished name
sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /home/vagrant/src/radiasoft/sirepo/etc/ldap_ldifs/config.ldif

# add admin password to backend
sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /home/vagrant/src/radiasoft/sirepo/etc/ldap_ldifs/admin_password.ldif

# allow admin database access
sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /home/vagrant/src/radiasoft/sirepo/etc/ldap_ldifs/admin_access.ldif

# create test base dn
sudo ldapadd -f /home/vagrant/src/radiasoft/sirepo/etc/ldap_ldifs/test_dn.ldif -D cn=admin,dc=example,dc=com -w vagrant

# create organizational unit (ou) for users (assigns permissions)
sudo ldapadd -f /home/vagrant/src/radiasoft/sirepo/etc/ldap_ldifs/test_ou.ldif -D cn=admin,dc=example,dc=com -w vagrant

# add prequisite schema to core schema
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /etc/openldap/schema/cosine.ldif
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /etc/openldap/schema/inetorgperson.ldif
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /etc/openldap/schema/nis.ldif

# add user to ou
sudo ldapadd -f /home/vagrant/src/radiasoft/sirepo/etc/ldap_ldifs/test_user.ldif -x -D cn=admin,dc=example,dc=com -w vagrant
"""

exec sirepo service http