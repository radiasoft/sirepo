#!/bin/bash
#
# Check for debug statements and run all tests
#
set -euo pipefail

test_err() {
    echo "$@" 1>&2
    return 1
}

test_js() {
    local jsfiles=( sirepo/package_data/static/js/*.js )
    test_no_prints '\s(srdbg|console.log|console.trace)\(' "${jsfiles[@]}"
    jshint --config=etc/jshint.conf "${jsfiles[@]}"
    if [[ ! ${sirepo_test_no_karma:-} ]]; then
        karma start etc/karma-conf.js
    fi
}

test_main() {
    test_js
    test_no_h5py
    export SIREPO_SRUNIT_CPU_DIV=$(
        python <<-'EOF'
import timeit;
print(round(100 * timeit.timeit("str().join(str(i) for i in range(1000000))", number=2)))
EOF
    )
    SIREPO_FEATURE_CONFIG_UI_WEBSOCKET=1 pykern test
    SIREPO_FEATURE_CONFIG_UI_WEBSOCKET=0 pykern ci run
}

test_no_h5py() {
    local f=( $(find sirepo -name \*.py | egrep -v '/(package_data|activait|flash|opal|radia|silas|warp|server.py|hdf5_util)') )
    local r=$(grep -l '^import.*h5py' "${f[@]}")
    if [[ $r ]]; then
        test_err "import h5py found in: $r"
    fi
}

test_no_prints() {
    local pat=$1
    shift
    local f=( $@ )
    local r=$(egrep -l "$pat" "${f[@]}")
    if [[ $r ]]; then
        test_err "$pat found in: $r"
    fi
}

test_main "$@"
