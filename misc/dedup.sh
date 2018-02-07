#!/bin/bash
#
# symlinks to user/src/*/lib files
#
src=$PWD/src

dedup_one() {
    local u=$1
    local f s
    for f in $u/*/lib/*; do
        if [[ -L $f ]]; then
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
    if [[ ! -d $src ]]; then
        echo 'Must be run from user directory' 1>&2
        exit 1
    fi
    for u in *; do
        if [[ $u =~ ^[a-zA-Z0-9]{8}$ ]]; then
            dedup_one "$u"
        fi
    done
}

dedup_main "$@"
