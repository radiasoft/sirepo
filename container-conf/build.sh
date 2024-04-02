#!/bin/bash

build_vars() {
    export sirepo_db_dir=/sirepo
    export sirepo_port=8000
    : ${build_image_base:=radiasoft/beamsim}
    local boot_dir=$build_run_user_home/.radia-run
    sirepo_boot=$boot_dir/start
    build_docker_cmd='["'"$sirepo_boot"'"]'
    build_is_public=1
    build_passenv='PYKERN_COMMIT SIREPO_COMMIT'
    : ${PYKERN_COMMIT:=} ${SIREPO_COMMIT:=}
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
    _sirepo_clone pykern "$PYKERN_COMMIT"
    pip install .
    cd ..
    _sirepo_clone sirepo "$SIREPO_COMMIT"
    pip install -e .
    sirepo srw create_predefined
    pip install .
    cd ..
}

sirepo_boot_init() {
    mkdir -p "$(dirname "$sirepo_boot")"
    build_replace_vars radia-run.sh "$sirepo_boot"
    chmod +x "$sirepo_boot"
}

_sirepo_clone() {
    declare repo=$1
    declare commit=$2
    git clone -q -c advice.detachedHead=false ${commit:+--branch "$commit"} --depth=1 https://github.com/radiasoft/"$repo"
    cd $repo
}

build_vars
