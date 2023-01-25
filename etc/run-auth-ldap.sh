#!/bin/bash
export SIREPO_AUTH_METHODS='guest:ldap'
exec sirepo service http
