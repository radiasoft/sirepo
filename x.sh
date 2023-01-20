set -eou pipefail
sirepo service uwsgi &
sirepo service nginx-proxy &
sirepo job_supervisor &

declare -a x=( $(jobs -p) )
# this doesn't kill uwsgi for some reason; TERM is better than KILL
trap "kill ${x[*]}" EXIT
wait -n