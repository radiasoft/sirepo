#!/bin/bash

# install and start, python-ldap needs openldap-devel
sudo yum -y install openldap-devel openldap-clients openldap-servers
pip install python-ldap
sudo systemctl start slapd

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