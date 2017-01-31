#!/bin/bash
set -e
set -x
docker run -it radiasoft/sirepo /bin/bash <<'END'
set -e
yum install nodejs
su - vagrant <<'EOF'
set -e
mkdir ~/src/radiasoft
for m in pykern sirepo; do
    git clone -q --depth 1 https://github.com/radiasoft/"$m"
    cd "$m"
    pip install -r requirements.txt
    python setup.py install
    cd ..
done
curl radia.run | bash -s code srw
cd sirepo
npm install jshint
bash test.sh
EOF
END
