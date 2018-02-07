#!/bin/bash
#
# removes reports older than N days (default: 3)
#
set -e -u -o pipefail
DEFAULT_DAYS=3

expunge_one() {
    local mmin=$1
    local u=$2
    for f in $(find "$u"/*/*/* -prune -type d -mmin +"$mmin"); do
        if [[ $f =~ /[a-zA-Z0-9]{8}/[^/]+$ ]]; then
            rm -rf "$f"
        fi
    done
}

expunge_main() {
    local days=${1:-$DEFAULT_DAYS}
    # sanity check number
    local mmin=$(( $days * 24 * 60 ))
    local u
    if [[ ! $PWD =~ /user$ ]]; then
        echo 'Must be run from user directory' 1>&2
        exit 1
    fi
    for u in *; do
        if [[ $u =~ ^[a-zA-Z0-9]{8}$ ]]; then
            expunge_one "$mmin" "$u"
        fi
    done
}

expunge_main "$@"
