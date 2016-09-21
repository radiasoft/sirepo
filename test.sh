#!/bin/bash
set -e
pyfiles=( $(find sirepo -name \*.py) )
pat='\s(pkdp|print)\('
if egrep "$pat" "${pyfiles[@]}"; then
    echo "$pat: remove all debugging calls" 1>&2
    exit 1
fi
set -x
./node_modules/jshint/bin/jshint --config=etc/jshint.conf sirepo/package_data/static/js/*.js
if [[ $PKSETUP_PYPI_PASSWORD ]]; then
    python setup.py pkdeploy
else
    python setup.py test
fi
