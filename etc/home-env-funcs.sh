#!/bin/bash

_sirepo_dev_mail=~/mail
_sirepo_dev_src=~/src/radiasoft/sirepo

sirepo_dev_add_admin() {
    declare u
    # POSIT: only uids in user and they don't have any specials
    for u in $(ls "$_sirepo_dev_src"/run/user); do
        sirepo roles add "$u" adm
    done
}

sirepo_dev_mail() {
    perl -n -e 'm{(http://\S+)} && print("$1\n")' $(ls -dt "$_sirepo_dev_mail"/* | head -n1)'"")'
}
