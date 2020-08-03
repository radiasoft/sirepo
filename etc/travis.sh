#!/bin/bash
set -eou pipefail
if ! [[ $TRAVIS_BRANCH == master && $TRAVIS_EVENT_TYPE == push ]]; then
    exit
fi
docker run -u vagrant -e PYKERN_PKCLI_GITHUB_USER -e PYKERN_PKCLI_GITHUB_PASSWORD -i radiasoft/python3:alpha /bin/bash -l <<'EOF'
set -eou pipefail
set -x
mkdir -p $HOME/src/radiasoft
cd $HOME/src/radiasoft
gcl pykern
cd pykern
pip install -q -e .
pykern github update_alpha_pending radiasoft/sirepo
EOF
