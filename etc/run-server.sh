#!/bin/bash
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_AUTH_EMAIL_FROM_EMAIL='support@radiasoft.net'
export SIREPO_AUTH_EMAIL_FROM_NAME='RadiaSoft Support'
export SIREPO_AUTH_EMAIL_SMTP_PASSWORD='n/a'
# POSIT: same as sirepo.auth.email._DEV_SMTP_SERVER
export SIREPO_AUTH_EMAIL_SMTP_SERVER='dev'
export SIREPO_AUTH_EMAIL_SMTP_USER='n/a'
export SIREPO_AUTH_METHODS='email:guest'
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
PYENV_VERSION=py3 pyenv exec sirepo service flask
