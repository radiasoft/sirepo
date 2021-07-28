#!/bin/bash
set -eou pipefail

SIREPO_AUTH_METHODS=bluesky \
    SIREPO_AUTH_BLUESKY_SECRET=bluesky \
    bash -l etc/run-jupyterhub.sh
