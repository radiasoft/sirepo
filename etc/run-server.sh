#!/bin/bash
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_FROM_EMAIL='support@radiasoft.net'
export SIREPO_FROM_NAME='RadiaSoft Support'
export SIREPO_SMTP_PASSWORD='n/a'
# POSIT: same as sirepo.smtp.DEV_SMTP_SERVER
export SIREPO_SMTP_SERVER='dev'
export SIREPO_SMTP_USER='n/a'
export SIREPO_MPI_CORES=2
case ${1:-} in
    docker)
        # POSIT: run-supervisor.sh
        export SIREPO_SRDB_ROOT=$HOME/tmp/sirepo-run
        mkdir -p "$SIREPO_SRDB_ROOT"
        ;;
    local)
        ;;
    nersc)
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Perlmutter@NERSC'
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
sirepo service server
