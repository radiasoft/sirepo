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
    # setup pyenv
    set +euo pipefail
    source ~/.bashrc
    set -euo pipefail
    cd "$_build_nsls2_guest_d"
    cd SRW/cpp/gcc
    make -j4 lib
    cd ../py
    make -j4 python
    cd ../..
    install -m 644 env/work/srw_python/{{srwl,uti}*.py,srwlpy*.so} \
        "$(python -c 'from distutils.sysconfig import get_python_lib as x; print(x())')"
    cd ../sirepo
    pip uninstall sirepo >& /dev/null || true
    pip install -r requirements.txt
    pip install .
    sirepo srw create_predefined
    cd /
    rm -rf "$_build_nsls2_guest_d"
}

build_nsls2_host_main() {
    cd "$(dirname "$0")"
    local s=$(basename "$0")
    local d=$PWD/tmp-nsls2
    rm -rf "$d"
    mkdir "$d"
    cp -a "$s" "$d"
    cd "$d"
    mkdir sirepo
    cp -a ../../{LICENSE,README.md,requirements.txt,setup.py,sirepo,.git} sirepo
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
RUN bash $_build_nsls2_guest_d/$s
EOF
    docker build --rm=true --tag=radiasoft/sirepo:nsls2 .
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
