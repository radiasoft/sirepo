#!/bin/bash
#
# Check for debug statements and run all tests
#
set -euo pipefail

test_jshint() {
    if [[ ! -x ./node_modules/jshint/bin/jshint ]]; then
        if ! type node >& /dev/null; then
            # Will fail in vag
            echo Installing nodejs 1>&2
            sudo dnf install -y -q nodejs
        fi
        echo Installing jshint 1>&2
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
    test_jshint
    if [[ -x ./node_modules/karma/bin/karma ]]; then
       ./node_modules/karma/bin/karma start etc/karma-conf.js
    fi
    py.test tests
    if [[ -n ${PKSETUP_PYPI_PASSWORD:+hide-secret} ]]; then
        python setup.py pkdeploy
    fi
}

test_no_prints() {
    local pat=$1
    shift
    local files=( $@ )
    if egrep "$pat" ${files[@]}; then
        echo "$pat: remove all debugging calls" 1>&2
        return 1
    fi
}

test_main "$@"
