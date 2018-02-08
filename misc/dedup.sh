#!/bin/bash
#
# symlinks to user/src/*/lib files
#
set -e -u -o pipefail
src=$PWD/src

dedup_one() {
    local u=$1
    local f s
    for f in $u/*/lib/*; do
        if [[ -L $f ]]; then
            # revert: cp "$f" z && rm "$f" && mv z "$f"
            continue
        fi
        s=${f/$u/$src}
        if [[ -r "$s" ]] && cmp -s "$s" "$f" >& /dev/null; then
            rm -f "$f"
            # CentOS 6 does not support --relative
            # ln -s --relative "$src" "$f"
            ln -s "../../../${f/$u/src}" "$f"
        fi
    done
}

dedup_main() {
    local u
    if [[ ! $PWD =~ /user$ ]]; then
        echo 'Must be run from user directory' 1>&2
        exit 1
    fi
    if [[ ! -d $src ]]; then
        mkdir "$src"
        local f=srw/lib/magn_meas_chx.zip
        local x=$(ls -tr */"$f" | tail -1)
        local s=$PWD/src
        (cd "${x%$f}" && rsync -avR */lib "$s")
        chmod -R a+rX "$src"
    fi
    for u in *; do
        if [[ $u =~ ^[a-zA-Z0-9]{8}$ ]]; then
            dedup_one "$u"
        fi
    done
}

dedup_main "$@"
