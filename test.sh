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
    pykern ci run
}

test_no_h5py() {
    local f=( $(find sirepo -name \*.py | egrep -v '/(package_data|activait|flash|opal|radia|rs4pi|silas|synergia|warp|server.py)') )
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
