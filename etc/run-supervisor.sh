#!/bin/bash
export PYKERN_PKDEBUG_CONTROL=
export PYKERN_PKDEBUG_OUTPUT=
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_FEATURE_CONFIG_JOB=1
export SIREPO_MPI_CORES=2
docker_image="radiasoft/sirepo:dev"
case ${1:-} in
    docker)
        if ! docker info >& /dev/null; then
            echo 'docker not installed. You need to run:

radia_run redhat-docker
'
            exit 1
        fi
        if  ! docker image inspect "$docker_image" >& /dev/null; then
            echo "$docker_image docker image not found. Pulling..."
            docker image pull "$docker_image"
        fi
        export SIREPO_JOB_DRIVER_MODULES=docker
        ;;
    local)
        export SIREPO_JOB_DRIVER_MODULES=local
        ;;
    nersc)
        if [[ ! ${2:-} || ! ${3:-} ]]; then
            echo 'you need to supply a proxy NERSC can reach and NERSC user '
            exit 1
        fi
        export SIREPO_JOB_DRIVER_MODULES=local:sbatch
        export SIREPO_JOB_DRIVER_SBATCH_HOST=cori.nersc.gov
        export SIREPO_JOB_DRIVER_SBATCH_SHIFTER_IMAGE=radiasoft/sirepo:sbatch
        export SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=/global/homes/${3::1}/$3/.pyenv/versions/py3/bin/sirepo
        export SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/global/cscratch1/sd/{sbatch_user}/sirepo-dev'
        export SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS=15
        export SIREPO_JOB_DRIVER_SBATCH_SUPERVISOR_URI=http://$2:8001
        export SIREPO_PKCLI_JOB_SUPERVISOR_IP=0.0.0.0
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Cori@NERSC'
        ;;
    sbatch)
        export SIREPO_JOB_DRIVER_MODULES=local:sbatch
        export SIREPO_JOB_DRIVER_SBATCH_HOST=${2:-$(hostname)}
        export SIREPO_JOB_DRIVER_SBATCH_CORES=2
        if [[ $SIREPO_JOB_DRIVER_SBATCH_HOST == $(hostname) ]]; then
            if [[ $(type -t sbatch) == '' ]]; then
                echo 'slurm not installed. You need to run:

radia_run slurm-dev
'
                exit 1
            fi
        else
            export SIREPO_JOB_DRIVER_SBATCH_CORES=4
        fi
        export SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=$HOME/.pyenv/versions/py3/bin/sirepo
        export SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/var/tmp/{sbatch_user}/sirepo'
        export SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS=5
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Vagrant Cluster'
        ;;
    *)
        echo 'usage: bash run-supervisor.sh [docker|local|sbatch [slurm host]|nersc proxy-host nersc-user]'
        exit 1
        ;;
esac
echo "${SIREPO_SIMULATION_DB_SBATCH_DISPLAY:-without sbatch}"
if [[ $SIREPO_JOB_DRIVER_MODULES =~ sbatch ]]; then
    export SIREPO_JOB_DRIVER_SBATCH_HOST_KEY="$(grep ^$SIREPO_JOB_DRIVER_SBATCH_HOST ~/.ssh/known_hosts || true)"
    if [[ ! $SIREPO_JOB_DRIVER_SBATCH_HOST_KEY ]]; then
        cat <<EOF 1>&2
you need to get the host key in ~/.ssh/known_hosts
ssh $SIREPO_JOB_DRIVER_SBATCH_HOST true
EOF
        exit 1
    fi
fi
PYENV_VERSION=py3 pyenv exec sirepo job_supervisor
