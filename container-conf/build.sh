#!/bin/bash

build_vars() {
    export sirepo_db_dir=/sirepo
    export sirepo_port=8000
    build_image_base=radiasoft/beamsim
    export build_passenv=TRAVIS_BRANCH
    : ${TRAVIS_BRANCH:=}
    local boot_dir=$build_run_user_home/.radia-run
    sirepo_tini_file=$boot_dir/tini
    sirepo_boot=$boot_dir/start
    build_is_public=1
    build_docker_cmd='["'"$sirepo_tini_file"'", "--", "'"$sirepo_boot"'"]'
    build_dockerfile_aux="USER $build_run_user"
}

build_as_root() {
    umask 022
    build_yum install nodejs
    mkdir "$sirepo_db_dir"
    chown "$build_run_user:" "$sirepo_db_dir"
}

build_as_run_user() {
    . ~/.bashrc
    cd "$build_guest_conf"
    sirepo_boot_init
    sirepo_fix_srw
    sirepo_reinstall_pykern

    # sirepo
    git clone -q --depth=50 "--branch=${TRAVIS_BRANCH:-master}" \
        https://github.com/radiasoft/sirepo
    cd sirepo
    if [[ ${TRAVIS_COMMIT:+1} ]]; then
        git checkout -qf "$TRAVIS_COMMIT"
    fi
    pip install -r requirements.txt
    pip install .

    # test & deploy
    # npm gets ECONNRESET due to a node error, which shouldn't happen
    # https://github.com/nodejs/node/issues/3595
    npm install jshint >& /dev/null || true
    bash test.sh
    cd ..

}

sirepo_boot_init() {
    mkdir -p "$(dirname "$sirepo_boot")"
    build_replace_vars radia-run.sh "$sirepo_boot"
    chmod +x "$sirepo_boot"
    build_curl https://github.com/krallin/tini/releases/download/v0.9.0/tini > "$sirepo_tini_file"
    chmod +x "$sirepo_tini_file"

    # legacy init
    install -m 555 radia-run-sirepo.sh ~/bin/radia-run-sirepo

}

sirepo_fix_srw() {
    # Remove print statements from SRW
    # Patch srwlib.py to not print stuff
    local srwlib="$(python -c 'import srwlib; print srwlib.__file__')"
    # Trim .pyc to .py (if there)
    perl -pi.bak -e  's/^(\s+)(print)/$1pass#$2/' "${srwlib%c}"
}

sirepo_reinstall_pykern() {
    git clone -q --depth=50 https://github.com/radiasoft/pykern
    cd pykern
    pip uninstall -y pykern || true
    pip install .
    cd ..
}

build_vars
