#!/bin/bash

build_vars() {
    export sirepo_db_dir=/sirepo
    export sirepo_port=8000
    : ${build_image_base:=radiasoft/beamsim}
    local boot_dir=$build_run_user_home/.radia-run
    sirepo_boot=$boot_dir/start
    build_is_public=1
    build_docker_cmd='["'"$sirepo_boot"'"]'
}

build_as_root() {
    umask 022
    build_yum config-manager \
        --add-repo \
        https://download.docker.com/linux/fedora/docker-ce.repo
    build_yum install docker-ce-cli
    mkdir "$sirepo_db_dir"
    chown "$build_run_user:" "$sirepo_db_dir"
}

build_as_run_user() {
    install_source_bashrc
    cd "$build_guest_conf"
    umask 022
    sirepo_boot_init
    sirepo_fix_srw
    git clone -q --depth=50 https://github.com/radiasoft/pykern
    git clone ${SIREPO_COMMIT:+--branch $SIREPO_COMMIT} -q --depth=50 https://github.com/radiasoft/sirepo
    cd pykern
    pip uninstall -y pykern || true
    pip install .
    cd ../sirepo
    pip install -e .
    sirepo srw create_predefined
    pip uninstall -y sirepo
    pip install .
    cd ..
}

sirepo_boot_init() {
    mkdir -p "$(dirname "$sirepo_boot")"
    build_replace_vars radia-run.sh "$sirepo_boot"
    chmod +x "$sirepo_boot"
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
