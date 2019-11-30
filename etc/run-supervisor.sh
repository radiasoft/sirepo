#!/bin/bash
export PYKERN_PKDEBUG_CONTROL=
export PYKERN_PKDEBUG_OUTPUT=
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_FEATURE_CONFIG_JOB_SUPERVISOR=1
export SIREPO_JOB_DRIVER_MODULES=local:sbatch
export SIREPO_JOB_DRIVER_SBATCH_HOST=v2.radia.run
export SIREPO_JOB_DRIVER_SBATCH_HOST_KEY="$(grep ^$SIREPO_JOB_DRIVER_SBATCH_HOST ~/.ssh/known_hosts || true)"
if [[ ! $SIREPO_JOB_DRIVER_SBATCH_HOST_KEY ]]; then
    cat <<EOF 1>&2
you need to get the host key in ~/.ssh/known_hosts
ssh $SIREPO_JOB_DRIVER_SBATCH_HOST
EOF
    exit 1
fi
export SIREPO_JOB_SUPERVISOR_URI=ws://$(hostname):8001
export SIREPO_MPI_CORES=4
export SIREPO_PKCLI_JOB_SUPERVISOR_IP=$(hostname --ip)
export SIREPO_SIMULATION_DB_SBATCH_DISPLAY=v2
PYENV_VERSION=py3 pyenv exec sirepo job_supervisor
