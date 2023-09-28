#!/bin/bash

sirepo_add_admin() {
    declare u
    # POSIT: only uids in user and they don't have any specials
    for u in $(ls ~/src/radiasoft/sirepo/run/user); do
        sirepo roles add "$u" adm
    done
}

sirepo_mail() {
    # xargs trims whitespace
    grep 'http://' $(ls -dt ~/mail/* | head -n1) | xargs
}
