#!/bin/bash
# TODO(BG): Need to finish testing installation before relevant for review. So far narrowed 

# primary cause of failed wheel generation, should not be needed
# pip install --upgrade pip

# install prerequisites, do not group install (install needed packages which are likely already there), also dnf not yum
# Tools likely missing (if any): Maybe MSYS2 if windows, SDF, WML
# sudo yum groupinstall "Development tools"
# don't need python-devel, likely don't need openldap-devel if have clients and servers, also dnf not yum
# sudo yum install openldap-devel python-devel

# secondary cause of failed wheel generation, setup tools should not be needed but wheel update occasionally
pip install --upgrade setuptools wheel

# main installs, don't install python-ldap??? Also dnf not yum
pip install python-ldap
sudo yum -y install openldap-clients openldap-servers

# don't need to enable slapd for now, might later to make script idempotent
sudo systemctl start slapd
# sudo systemctl enable slapd

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