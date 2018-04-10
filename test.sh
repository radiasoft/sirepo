#!/bin/bash
#
# Check for debug statements and run all tests
#
set -e

assert_no_prints() {
    local pat=$1
    shift
    local files=( $@ )
    if egrep "$pat" ${files[@]}; then
        echo "$pat: remove all debugging calls" 1>&2
        exit 1
    fi
}

pyfiles=( $(find sirepo -name \*.py | sort) )
assert_no_prints '\s(pkdp|print)\(' "${pyfiles[@]}"
jsfiles=( sirepo/package_data/static/js/*.js )
assert_no_prints '\s(srdbg|console.log)\(' "${jsfiles[@]}"
if [[ -x ./node_modules/jshint/bin/jshint ]]; then
    ./node_modules/jshint/bin/jshint --config=etc/jshint.conf "${jsfiles[@]}"
fi
if [[ -x ./node_modules/karma/bin/karma ]]; then
   ./node_modules/karma/bin/karma start etc/karma-conf.js
fi
python setup.py test
if [[ -n ${PKSETUP_PYPI_PASSWORD:+hide-secret} ]]; then
    python setup.py pkdeploy
fi
