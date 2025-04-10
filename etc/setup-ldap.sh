#!/bin/bash
set -eou pipefail
# install and start
sudo yum -y install openldap-clients openldap-servers
pip install ldap3
sudo systemctl start slapd
sudo systemctl enable slapd

# assign default root and appended distunguished name
cd "$(dirname "$0")"/ldap_ldifs
sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f config.ldif

# add admin password to backend
sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f admin_password.ldif

# allow admin database access
sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f admin_access.ldif

# create test base dn
sudo ldapadd -f test_dn.ldif -D cn=admin,dc=example,dc=com -w vagrant

# create organizational unit (ou) for users (assigns permissions)
sudo ldapadd -f test_ou.ldif -D cn=admin,dc=example,dc=com -w vagrant

# add prequisite schema to core schema
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /etc/openldap/schema/cosine.ldif
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /etc/openldap/schema/inetorgperson.ldif
sudo ldapadd -Y EXTERNAL -H ldapi:// -f /etc/openldap/schema/nis.ldif

# add user to ou
sudo ldapadd -f test_user.ldif -x -D cn=admin,dc=example,dc=com -w vagrant
