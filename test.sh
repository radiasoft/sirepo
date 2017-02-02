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
if [[ $PKSETUP_PYPI_PASSWORD ]]; then
    python setup.py pkdeploy
else
    python setup.py test
fi
