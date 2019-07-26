#!/bin/bash
#
# Check for debug statements and run all tests
#
set -euo pipefail

test_err() {
    test_msg "$@"
    return 1
}

test_jshint() {
    if [[ ! -x ./node_modules/jshint/bin/jshint ]]; then
        if ! type node >& /dev/null; then
            # Will fail in vag
            test_msg Installing nodejs
            sudo dnf install -y -q nodejs
        fi
        test_msg Installing jshint
        # npm gets ECONNRESET due to a node error, which shouldn't happen
        # https://github.com/nodejs/node/issues/3595
        npm install jshint >& /dev/null || true
    fi
    ./node_modules/jshint/bin/jshint --config=etc/jshint.conf "${jsfiles[@]}"
}

test_main() {
    local pyfiles=( $(find sirepo -name \*.py | sort) )
    test_no_prints '\s(pkdp|print)\(' "${pyfiles[@]}"
    local jsfiles=( sirepo/package_data/static/js/*.js )
    test_no_prints '\s(srdbg|console.log)\(' "${jsfiles[@]}"
    test_no_h5py
    test_jshint
    if [[ -x ./node_modules/karma/bin/karma ]]; then
       ./node_modules/karma/bin/karma start etc/karma-conf.js
    fi
    py.test tests
    if [[ -n ${PKSETUP_PYPI_PASSWORD:+hide-secret} ]]; then
        python setup.py pkdeploy
    fi
}

test_msg() {
    echo "$@" 1>&2
}

test_no_h5py() {
    local f=( $(find sirepo -name \*.py | egrep -v '/(package_data|flash|rs4pi|synergia|warp|server.py)') )
    local r=$(grep -l 'import.*h5py' "${f[@]}")
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
