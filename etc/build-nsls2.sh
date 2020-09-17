#!/bin/bash
set -euo pipefail

_build_nsls2_guest_d=/home/vagrant/tmp-nsls2

build_nsls2_docker_clean() {
    local x=( $(docker ps -a -q --filter status=exited) )
    if [[ ${x:-} ]]; then
        echo Removing containers: "${x[@]}"
        docker rm "${x[@]}" || true
    fi
    x=( $(docker images --filter dangling=true -q) )
    if [[ ${x:-} ]]; then
        echo Removing images: "${x[@]}"
        docker rmi "${x[@]}" || true
    fi
}

build_nsls2_guest_main() {
    set -x
    # setup pyenv
    set +euo pipefail
    source ~/.bashrc
    set -euo pipefail
    cd "$_build_nsls2_guest_d"
    source ./env
    cd SRW/cpp/gcc
    make -j4 lib
    cd ../py
    make -j4 python
    cd ../..
    install -m 644 env/work/srw_python/{{srwl,uti}*.py,srwlpy*.so} \
            "$(python -c 'from distutils.sysconfig import get_python_lib as x; print(x())')"
    local d
    for d in pykern sirepo; do
        pip uninstall -y "$d" >& /dev/null || true
        cd ../"$d"
        pip install .
    done
    sirepo srw create_predefined
    cd /
    rm -rf "$_build_nsls2_guest_d"
}

build_nsls2_host_main() {
    set -x
    cd "$(dirname "$0")"
    local s=$(basename "$0")
    local d=$PWD/tmp-nsls2
    rm -rf "$d"
    mkdir "$d"
    cp -a "$s" "$d"
    cd "$d"
    cat <<EOF >> env
export http_proxy=${http_proxy:-}
export https_proxy=${https_proxy:-}
EOF
    cp -a ../../../pykern .
    mkdir sirepo
    cp -a ../../{LICENSE,README.md,requirements.txt,setup.py,sirepo,.git} sirepo
    (git --git-dir=$HOME/src/radiasoft/sirepo/.git describe --all --tags --long --always --dirty; date) > sirepo/VERSION.txt
    mkdir -p SRW/env/work/srw_python
    cp -a ~/src/ochubar/SRW/env/work/srw_python/[a-z]*py SRW/env/work/srw_python
    cp -a ~/src/ochubar/SRW/{cpp,Makefile} SRW
    perl -pi -e "s/'fftw'/'sfftw'/" SRW/cpp/py/setup.py
    perl -pi -e 's/-lfftw/-lsfftw/; s/\bcc\b/gcc/; s/\bc\+\+/g++/' SRW/cpp/gcc/Makefile
    echo 'Updating: radiasoft/sirepo:dev'
    docker pull -q radiasoft/sirepo:dev
    cat > Dockerfile <<EOF
FROM radiasoft/sirepo:dev
USER vagrant
ADD --chown=vagrant:vagrant . $_build_nsls2_guest_d
ADD --chown=vagrant:vagrant sirepo/VERSION.txt /
RUN bash $_build_nsls2_guest_d/$s
EOF
    docker build --rm=true --network=host --build-arg http_proxy=$http_proxy --build-arg https_proxy=$https_proxy --tag=radiasoft/sirepo:nsls2 .
    # docker build --rm=true --network=host --tag=radiasoft/sirepo:nsls2 .
    cd ..
    rm -rf "$d"
    build_nsls2_docker_clean
}

build_nsls2_main() {
    if [[ -e /.dockerenv ]]; then
        build_nsls2_guest_main
    else
        build_nsls2_host_main
    fi

}

build_nsls2_main
