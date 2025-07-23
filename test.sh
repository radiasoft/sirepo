#!/bin/bash
#
# Check for debug statements and run all tests
#
set -euo pipefail

_KARMA_SUCCESS='TOTAL: 41 SUCCESS$'

_err() {
    _msg "$@"
    return 1
}

_js() {
    local jsfiles=( sirepo/package_data/static/js/*.js )
    _no_prints "${jsfiles[@]}"
    _no_smart_quotes "${jsfiles[@]}"
    jshint --config=etc/jshint.conf "${jsfiles[@]}"
    if [[ ! ${sirepo_test_no_karma:-} ]]; then
        declare r=$(karma start etc/karma-conf.js 2>&1 || true)
        if ! [[ $r =~ $_KARMA_SUCCESS ]]; then
            _err "$r"
        fi
    fi
}

_main() {
    _js
    _no_h5py
    export SIREPO_SRUNIT_CPU_DIV=$(
        python <<-'EOF'
import timeit;
print(round(100 * timeit.timeit("str().join(str(i) for i in range(1000000))", number=2)))
EOF
    )
    export PYKERN_PKCLI_TEST_MAX_PROCS=4
    export PYKERN_PKCLI_TEST_MAX_CASE_SECS=360
    export SIREPO_MPI_CORES=2
    pykern ci run
}

_msg() {
    echo "$@" 1>&2
}

_no_h5py() {
    local f=( $(find sirepo -name \*.py | egrep -v '/(package_data|activait|flash|omega|opal|radia|silas|warp|server.py|hdf5_util|madx|canvas|elegant|openmc)') )
    local r=$(grep -l '^import.*h5py' "${f[@]}")
    if [[ $r ]]; then
        _err "import h5py found in: $r"
    fi
}

_no_pattern() {
    local pat=$1
    shift
    local f=( $@ )
    local r=$(egrep -l "$pat" "${f[@]}")
    if [[ $r ]]; then
        _err "$pat found in: $r"
    fi
}

_no_prints() {
    _no_pattern '\s(srdbg|console.log|console.trace)\(' $@
}

_no_smart_quotes() {
    _no_pattern '(“|”|‘|’)' $@
}

_main "$@"
