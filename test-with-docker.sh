#!/bin/bash
set -e -x
docker run -i radiasoft/sirepo /bin/bash -e -x <<'END'
curl -s -S -L https://rpm.nodesource.com/setup_4.x | bash
yum install -y -q nodejs
echo "vagrant ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/vagrant
chmod 440 /etc/sudoers.d/vagrant
su - vagrant <<'EOF'
set -e -x
mkdir ~/src/radiasoft
for m in pykern sirepo; do
    git clone -q --depth 1 https://github.com/radiasoft/"$m"
    cd "$m"
    git checkout robnagler
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
