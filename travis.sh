#!/bin/bash
set -e
set -x
trap 'echo FAILED' ERR
if [[ $TRAVIS_BRANCH != master && $TRAVIS_EVENT_TYPE != push ]]; then
    echo 'Not a master push so skipping'
    exit
fi
# "python setup.py --version" doesn't seem to work on travis so
# this emulates what pkssetup.py does to get it from the git branch
v=$(git log -1 --format=%ct "${TRAVIS_COMMIT:-$TRAVIS_BRANCH}")
export build_version=$(python -c "import datetime as d; print d.datetime.fromtimestamp(float($v)).strftime('%Y%m%d.%H%M%S')")

# Make sure some vars are defined that might not be
: ${PKSETUP_PKDEPLOY_IS_DEV:=}
: ${PKSETUP_PYPI_IS_TEST:=}
: ${RADIASOFT_DOCKER_LOGIN:=}
export build_passenv='
    PKSETUP_PKDEPLOY_IS_DEV
    PKSETUP_PYPI_IS_TEST
    PKSETUP_PYPI_PASSWORD
    PKSETUP_PYPI_USER
    RADIASOFT_DOCKER_LOGIN
    TRAVIS_BRANCH
    TRAVIS_COMMIT
'
# Make sure all the variables are exported
export $build_passenv
git clone https://github.com/radiasoft/containers
cd containers
if [[ -n $RADIASOFT_DOCKER_LOGIN ]]; then
    (
        umask 077
        mkdir ~/.docker
        # Avoid echoing in log if set -x
        perl -e 'print($ENV{"RADIASOFT_DOCKER_LOGIN"})' > ~/.docker/config.json
    )
    export build_push=1
fi
bin/build docker radiasoft/sirepo
echo PASSED
