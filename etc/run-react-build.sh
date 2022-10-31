#!/bin/bash
#
# Run a dev server with a static react build
set -euo pipefail
cd "$(dirname "$0")"/../react
rm -rf build
npm run-script build
cd ..
rm sirepo/package_data/static/react
ln -s ../../../react/build sirepo/package_data/static/react
export SIREPO_SERVER_REACT_SERVER=build
export SIREPO_PKCLI_SERVICE_REACT_PORT=
sirepo service http
