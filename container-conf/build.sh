#!/bin/bash

build_vars() {
    export sirepo_db_dir=/sirepo
    export sirepo_port=8000
    : ${build_image_base:=radiasoft/beamsim}
    local boot_dir=$build_run_user_home/.radia-run
    sirepo_boot=$boot_dir/start
    build_docker_cmd='["'"$sirepo_boot"'"]'
    build_is_public=1
    build_passenv='PYKERN_BRANCH RSLUME_BRANCH SIREPO_BRANCH'
    : ${PYKERN_BRANCH:=} ${RSLUME_BRANCH:=} ${SIREPO_BRANCH:=}
}

build_as_root() {
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
    _sirepo_pip_install pykern "$PYKERN_BRANCH"
    _sirepo_pip_install sirepo "$SIREPO_BRANCH"
    _sirepo_pip_install rslume "$RSLUME_BRANCH"
    _sirepo_test_static_files
}

sirepo_boot_init() {
    mkdir -p "$(dirname "$sirepo_boot")"
    build_replace_vars radia-run.sh "$sirepo_boot"
    chmod +x "$sirepo_boot"
}

_sirepo_pip_install() {
    declare repo=$1
    declare branch=$2
    git clone -q -c advice.detachedHead=false ${branch:+--branch "$branch"} --depth=1 https://github.com/radiasoft/"$repo"
    cd "$repo"
    if [[ $repo == sirepo ]]; then
        pip install -e .
        sirepo srw create_predefined
    fi
    pip install .
    cd - &> /dev/null
    rm -rf "$repo"
}

_sirepo_test_static_files() {
    mkdir static_files_tmp
    sirepo static_files gen static_files_tmp
    declare c=$(find static_files_tmp | wc -l)
    if (( c < 100 )); then
        install_err "too few static files count=$c < 100"
    fi
}

build_vars
