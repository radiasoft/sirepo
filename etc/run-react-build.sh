#!/bin/bash
#
# Run a dev server with a static react build
set -euo pipefail
if [[ ! ${run_react_build_no:-} ]]; then
    cd "$(dirname "$0")"/../react
    rm -rf build
    npm run-script build
    cd ..
    rm -f sirepo/package_data/static/react
    ln -s ../../../react/build sirepo/package_data/static/react
fi
export SIREPO_SERVER_REACT_SERVER=build
export SIREPO_PKCLI_SERVICE_REACT_PORT=
exec sirepo service http
