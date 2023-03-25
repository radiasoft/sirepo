#! /bin/bash
set -euo pipefail

trap "kill -- -$$" EXIT

SIREPO_FEATURE_CONFIG_RAYDATA_CATALOG_NAMES='chx:csx' \
    SIREPO_FEATURE_CONFIG_RAYDATA_SCAN_MONITOR_DB_DIR="~/src/radiasoft/sirepo/run/raydata" \
    SIREPO_FEATURE_CONFIG_RAYDATA_SCAN_MONITOR_NOTEBOOK_DIR="~/src/radiasoft/raydata/raydata/package_data" \
    sirepo raydata scan_monitor &
SIREPO_FEATURE_CONFIG_SIM_TYPES=raydata:elegant \
    sirepo service http &
wait
