#!/bin/bash
export PYKERN_PKDEBUG_CONTROL=
export PYKERN_PKDEBUG_OUTPUT=
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_FEATURE_CONFIG_JOB=1
export SIREPO_JOB_DRIVER_MODULES=local:sbatch

if [[ ${1:-} != nersc ]]; then
    export SIREPO_JOB_DRIVER_SBATCH_CORES=4
    export SIREPO_JOB_DRIVER_SBATCH_HOST=v8.radia.run
    export SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=/home/vagrant/.pyenv/versions/py3/bin/sirepo
    export SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/var/tmp/{sbatch_user}/sirepo'
    export SIREPO_JOB_DRIVER_SBATCH_USER=vagrant
    export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='V8 Cluster'
    export SIREPO_JOB_SUPERVISOR_URI=http://v.radia.run:8001
    export SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS=5
else
    export SIREPO_JOB_DRIVER_SBATCH_HOST=cori.nersc.gov
    export SIREPO_JOB_DRIVER_SBATCH_SHIFTER_IMAGE=radiasoft/sirepo:sbatch
    export SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=/global/homes/n/nagler/.pyenv/versions/py3/bin/sirepo
    export SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/global/cscratch1/sd/{sbatch_user}/sirepo'
    export SIREPO_JOB_DRIVER_SBATCH_USER=nagler
    export SIREPO_JOB_SUPERVISOR_URI=http://fnl7i.bivio.biz:8001
    export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Cori@NERSC'
    export SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS=15
fi
echo "$SIREPO_SIMULATION_DB_SBATCH_DISPLAY"
export SIREPO_JOB_DRIVER_SBATCH_HOST_KEY="$(grep ^$SIREPO_JOB_DRIVER_SBATCH_HOST ~/.ssh/known_hosts || true)"
if [[ ! $SIREPO_JOB_DRIVER_SBATCH_HOST_KEY ]]; then
    cat <<EOF 1>&2
you need to get the host key in ~/.ssh/known_hosts
ssh $SIREPO_JOB_DRIVER_SBATCH_HOST true
EOF
    exit 1
fi
export SIREPO_MPI_CORES=4
export SIREPO_PKCLI_JOB_SUPERVISOR_IP=$(hostname --ip)
PYENV_VERSION=py3 pyenv exec sirepo job_supervisor
