#!/bin/bash
#
# Check for debug statements and run all tests
#
set -euo pipefail

test_err() {
    test_msg "$@"
    return 1
}

test_js() {
    if [[ ! -x ./node_modules/karma/bin/karma || ! -x ./node_modules/jshint/bin/jshint ]]; then
        npm install
    fi
    npm run lint -- "${jsfiles[@]}"
    if [[ ! ${sirepo_test_no_karma:-} ]]; then
        npm run test
    fi
}

test_main() {
    local pyfiles=( $(find sirepo -name \*.py | sort) )
    test_no_prints '\s(pkdp|print)\(' "${pyfiles[@]}"
    local jsfiles=( sirepo/package_data/static/js/*.js )
    test_no_prints '\s(srdbg|console.log)\(' "${jsfiles[@]}"
    test_no_h5py
    test_js
    pykern test
    if [[ -n ${PKSETUP_PYPI_PASSWORD:+hide-secret} ]]; then
        python setup.py pkdeploy
    fi
}

test_msg() {
    echo "$@" 1>&2
}

test_no_h5py() {
    local f=( $(find sirepo -name \*.py | egrep -v '/(package_data|flash|opal|radia|rs4pi|silas|synergia|warp|server.py)') )
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
