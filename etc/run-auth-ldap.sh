#!/bin/bash
export SIREPO_AUTH_METHODS='guest:ldap'
export PYKERN_PKDEBUG_WANT_PID_TIME=1

exec sirepo service http
