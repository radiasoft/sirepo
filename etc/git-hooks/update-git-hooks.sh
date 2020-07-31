#!/bin/bash

b="/home/vagrant/src/radiasoft/sirepo"
for f in 'merge' 'commit'; do
    ln -fs "$b/etc/git-hooks/post-master-change" "$b/.git/hooks/post-$f"
    chmod +x "$b/.git/hooks/post-$f"
done
