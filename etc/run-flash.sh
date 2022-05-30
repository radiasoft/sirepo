#!/bin/bash
set -eou pipefail

export SIREPO_FEATURE_CONFIG_PROPRIETARY_OAUTH_SIM_TYPES=flash
if [[ ! ${SIREPO_SIM_OAUTH_FLASH_KEY:-} || ! ${SIREPO_SIM_OAUTH_FLASH_SECRET:-} ]]; then
    echo 'You must set $SIREPO_SIM_OAUTH_FLASH_KEY and $SIREPO_SIM_OAUTH_FLASH_SECRET' 1>&2
    exit 1
fi
sirepo service http
