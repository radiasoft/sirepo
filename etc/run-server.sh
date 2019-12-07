#!/bin/bash
export PYKERN_PKDEBUG_CONTROL=
export PYKERN_PKDEBUG_OUTPUT=
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_FEATURE_CONFIG_JOB=1
export SIREPO_JOB_SUPERVISOR_URI=http://$(hostname):8001
export SIREPO_MPI_CORES=2
case ${1:-} in
    docker|local)
        ;;
    nersc)
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Cori@NERSC'
        ;;
    sbatch)
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Vagrant Cluster'
        ;;
    *)
        echo 'usage: bash run-server.sh [docker|local|nersc|sbatch]'
        exit 1
        ;;
esac
echo "${SIREPO_SIMULATION_DB_SBATCH_DISPLAY:-without sbatch}"
PYENV_VERSION=py2 pyenv exec sirepo service http
