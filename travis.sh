#!/bin/bash
set -e
set -x
trap 'echo FAILED' ERR
if [[ $TRAVIS_BRANCH != master && $TRAVIS_EVENT_TYPE != push ]]; then
    echo 'Not a master push so skipping'
    exit
fi
pip install --upgrade pip setuptools tox pytest
pip install pykern
# Get sirepo version, need to right pad. Thanks setuptools!
build_version=$(python setup.py --version)
while (( ${#build_version} < 15 )); do
    build_version=${build_version}0
done
export build_version

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
