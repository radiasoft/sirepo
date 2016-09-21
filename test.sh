#!/bin/bash
set -e
assert_no_prints() {
    local pat=$1
    local files=$2
    #POSIT: No spaces in file names
    if egrep "$pat" $files; then
        echo "$pat: remove all debugging calls" 1>&2
        exit 1
    fi
}
assert_no_prints '\s(pkdp|print)\(' "$(find sirepo -name \*.py)"
assert_no_prints '\s(srdbg|console.log)\(' "$(echo sirepo/package_data/static/js/*.js)"
exit
set -x
./node_modules/jshint/bin/jshint --config=etc/jshint.conf sirepo/package_data/static/js/*.js
if [[ $PKSETUP_PYPI_PASSWORD ]]; then
    python setup.py pkdeploy
else
    python setup.py test
fi
