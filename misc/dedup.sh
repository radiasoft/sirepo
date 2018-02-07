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
            # UNDO: cp "$f" z && rm "$f" && mv xyzz "$f"
            continue
        fi
        s=${f/$u/$src}
        if [[ -r "$s" ]] && cmp -s "$s" "$f" >& /dev/null; then
            rm -f "$f"
            ln --relative -s "$s" "$f"
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
        (cd "${x%$f}" && rsync -avR */lib "$src")
        chmod -R a+rX "$src"
    fi
    for u in *; do
        if [[ $u =~ ^[a-zA-Z0-9]{8}$ ]]; then
            dedup_one "$u"
        fi
    done
}

dedup_main "$@"
