#!/bin/bash

build_vars() {
    export sirepo_db_dir=/sirepo
    export sirepo_port=8000
    : ${build_image_base:=radiasoft/beamsim}
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
    dnf config-manager \
        --add-repo \
        https://download.docker.com/linux/fedora/docker-ce.repo
    build_yum install nodejs docker-ce
    mkdir "$sirepo_db_dir"
    chown "$build_run_user:" "$sirepo_db_dir"
}

build_as_run_user() {
    . ~/.bashrc
    cd "$build_guest_conf"
    sirepo_boot_init
    git clone -q --depth=50 https://github.com/radiasoft/pykern
    git clone -q --depth=50 "--branch=${TRAVIS_BRANCH:-master}" \
        https://github.com/radiasoft/sirepo
    cd sirepo
    if [[ ${TRAVIS_COMMIT:+1} ]]; then
        git checkout -qf "$TRAVIS_COMMIT"
    fi
    local p
    for p in py3 py2; do
        pyenv global "$p"
        sirepo_fix_srw
        cd ../pykern
        pip uninstall -y pykern || true
        pip install .
        cd ../sirepo
        pip install -r requirements.txt
        pip install .
    done

    bash test.sh
    cd ..
    build_run_user_home_chmod_public
}

sirepo_boot_init() {
    mkdir -p "$(dirname "$sirepo_boot")"
    build_replace_vars radia-run.sh "$sirepo_boot"
    chmod +x "$sirepo_boot"
    build_curl https://github.com/krallin/tini/releases/download/v0.18.0/tini > "$sirepo_tini_file"
    chmod +x "$sirepo_tini_file"
}

sirepo_fix_srw() {
    # Remove print statements from SRW
    # Patch srwlib.py to not print stuff
    local srwlib="$(python -c 'import srwlib, sys; sys.stdout.write(srwlib.__file__)')"
    if [[ ! -f $srwlib ]]; then
        install_err 'failed to find srwlib'
    fi
    # Trim .pyc to .py (if there)
    perl -pi.bak -e  's/^(\s+)(print)/$1pass#$2/' "${srwlib%c}"
}

build_vars
