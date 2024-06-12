#!/bin/bash
export PYKERN_PKDEBUG_WANT_PID_TIME=1
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
        # POSIT: run-server.sh
        export SIREPO_SRDB_ROOT=$HOME/tmp/sirepo-run
        mkdir -p "$SIREPO_SRDB_ROOT"
        export SIREPO_JOB_DRIVER_MODULES=docker
        ;;
    local)
        export SIREPO_JOB_DRIVER_MODULES=local
        ;;
    nersc)
        if [[ ! ${2:-} || ! ${3:-} ]]; then
            echo 'you need to supply a host:port (proxy) NERSC can reach and NERSC user '
            exit 1
        fi
        supervisor_proxy=$2
        nersc_user=$3
        export SIREPO_JOB_DRIVER_MODULES=local:sbatch
        export SIREPO_JOB_DRIVER_SBATCH_HOST=perlmutter-p1.nersc.gov
        export SIREPO_JOB_DRIVER_SBATCH_SHIFTER_IMAGE="${SIREPO_JOB_DRIVER_SBATCH_SHIFTER_IMAGE:-$docker_image}"
        export SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=/global/homes/${nersc_user::1}/$nersc_user/.pyenv/versions/$(pyenv version-name)/bin/sirepo
        export SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/pscratch/sd/{sbatch_user:.1}/{sbatch_user}/sirepo-dev'
        export SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS=15
        export SIREPO_JOB_DRIVER_SBATCH_SUPERVISOR_URI=http://$supervisor_proxy
        export SIREPO_PKCLI_JOB_SUPERVISOR_IP=0.0.0.0
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Perlmutter@NERSC'
        ;;
    sbatch)
        export SIREPO_JOB_DRIVER_MODULES=local:sbatch
        export SIREPO_JOB_DRIVER_SBATCH_HOST=${2:-localhost}
        export SIREPO_JOB_DRIVER_SBATCH_CORES=2
        export SIREPO_JOB_DRIVER_SBATCH_NODES=1
        if [[ $SIREPO_JOB_DRIVER_SBATCH_HOST =~ ^(localhost|$(hostname --fqdn)) ]]; then
            if [[ $(type -t sbatch) == '' ]]; then
                echo 'slurm not installed. You need to run:

radia_run slurm-dev
'
                exit 1
            fi
        else
            export SIREPO_JOB_DRIVER_SBATCH_CORES=4
        fi
        export SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=$(pyenv which sirepo)
        export SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/var/tmp/{sbatch_user}/sirepo'
        export SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS=5
        export SIREPO_SIMULATION_DB_SBATCH_DISPLAY='Vagrant Cluster'
	# In dev the node goes down randomly. This resets it.
	sudo scontrol << EOF
update NodeName=debug State=DOWN Reason="undraining"
update NodeName=debug State=RESUME
EOF
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

ssh ${nersc_user+$nersc_user@}$SIREPO_JOB_DRIVER_SBATCH_HOST true
EOF
        exit 1
    fi
fi
sirepo job_supervisor
