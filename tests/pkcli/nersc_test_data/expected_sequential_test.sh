#!/bin/bash
set -eou pipefail
cd sirepo_run_dir
export SIREPO_MPI_CORES=1
export PYKERN_PKCONFIG_CHANNEL=dev
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export PYTHONUNBUFFERED=1
export SIREPO_AUTH_LOGGED_IN_USER=someuser
export SIREPO_SIMULATION_DB_LOGGED_IN_USER=someuser
export PYTHONPATH=
export PYTHONSTARTUP=
perl -p -e "s<sirepo_run_dir><$PWD>" '/home/vagrant/src/radiasoft/sirepo/sirepo/package_data/nersc_test/nersc_sequential.json' > 'jobCmdIn.json'
exec sirepo job_cmd jobCmdIn.json
