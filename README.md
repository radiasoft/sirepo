# sirepo

# THIS IS ALPHA SOFTWARE

Sirepo is a scientific application framework, currently for particle accelator codes.
Sirepo runs inside a Python web server.

You can use our
[curl installer on your Mac, PC (Cygwin only), or Linux box](https://github.com/radiasoft/download/blob/master/README.md)
as follows:

```bash
$ mkdir sirepo
$ cd sirepo
$ curl radia.run | bash
```

For this to work, you will need to [install the prerequisites](https://github.com/radiasoft/download/blob/master/README.md#requirements).

[API Documentation is available on Read the Docs.](http://sirepo.readthedocs.org)

### Manual Install with Docker

You can start Sirepo with [Docker](https://www.docker.com/).

If you are running Docker as an ordinary user (recommended), use the following:

```bash
$ docker run -it --rm -p 8000:8000 -v "$PWD:/vagrant" radiasoft/sirepo /radia-run "$(id -u)" "$(id -g)" /home/vagrant/bin/radia-run-sirepo /vagrant 8000
```

The `/radia-run` command ensures the guest's user can read/write files from the
current directory, which is where the database and other files will be stored.

Then visit the following link:

[http://localhost:8000/light](http://localhost:8000/light)

You can run sirepo in an emphemeral container as root, but without
storing files on the host:

```bash
# docker run -it --rm -p 8000:8000 -u vagrant radiasoft/sirepo bash -l -c 'radia-run-sirepo "$HOME" 8000'
```

### Manual Install with Vagrant

You can start Sirepo with [Vagrant](https://www.vagrantup.com/).

First create a `Vagrantfile` by copy-and-pasting this into a shell:

```bash
cat > Vagrantfile <<'EOF'
Vagrant.configure(2) do |config|
  config.vm.box = "radiasoft/sirepo"
  config.vm.network "forwarded_port", guest: 8000, host: 8000
  config.vm.synced_folder ".", "/vagrant", disabled: true
end
EOF
```

Boot the machine:

```bash
vagrant up
```

The images is 2.5GB so this will take some time.

If it's your first time running Vagrant, it will ask to install VirtualBox.

Follow the prompts

You can run Sirepo with a single command:

```bash
vagrant ssh -c '. ~/.bashrc; sirepo service http'
```

Or, if you would like to do development:

```bash
vagrant ssh
cd src/radiasoft
pip uninstall sirepo pykern
git clone https://github.com/radiasoft/pykern
cd pykern
pip install -e .
cd ..
git clone https://github.com/radiasoft/sirepo
cd sirepo
pip install -e .
sirepo service http
```

Then visit the following link:

[http://localhost:8000/light](http://localhost:8000/light)

#### Sharing Folder with Vagrant VM

Note that if you want to transfer files to the virtual machine,
you'll need to install the
[vagrant-vbguest plugin](https://github.com/dotless-de/vagrant-vbguest)
and remove the following line from the `Vagrantfile`:

```text
config.vm.synced_folder ".", "/vagrant", disabled: true
```

### Angular Testing

In order to test, you need to install Xvfb, nodejs (v4+), and google-chrome.

[Extensive tutorial on Angular Testing from 2013, which gives advice on jasmine testing, but uses obsolete scenario runner.](http://www.yearofmoo.com/2013/01/full-spectrum-testing-with-angularjs-and-karma.html)

[Advice on how to test better](http://www.yearofmoo.com/2013/09/advanced-testing-and-debugging-in-angularjs.html#writing-efficient-tests)

Install node globally as root:

```bash
curl -s -S -L https://rpm.nodesource.com/setup_4.x | bash
yum -y install nodejs
```

Install Xvfb globally as root. It runs as vagrant:

```bash
yum install xorg-x11-server-Xvfb
cat > /etc/systemd/system/Xvfb.service <<'EOF'
[Unit]
Description=Xvfb
After=network.target

[Service]
User=vagrant
SyslogIdentifier=%p
# -noreset fixes memory leak issue with other flags described here:
# http://blog.jeffterrace.com/2012/07/xvfb-memory-leak-workaround.html
# Start with screen 10, because we use visible X11 apps on VMs.
# Small screen size to save memory
# RANDR needed for chrome
ExecStart=/usr/bin/Xvfb -ac -extension RANDR -noreset -screen 0 1024x768x8

[Install]
WantedBy=multi-user.target
EOF
systemctl enable Xvfb
systemctl start Xvfb
```

Install Chrome globally as root:

```bash
cat << 'EOF' > /etc/yum.repos.d/google-chrome.repo
[google-chrome]
name=google-chrome - $basearch
baseurl=http://dl.google.com/linux/chrome/rpm/stable/$basearch
enabled=1
gpgcheck=1
gpgkey=https://dl-ssl.google.com/linux/linux_signing_key.pub
EOF
yum install -y google-chrome-stable
```

#### Karma (Angular unit testing)

The tests are located in `tests/karma`.
[Tutorial on karma and jasmine.](https://daveceddia.com/testing-angular-part-1-karma-setup/)

As user install node modules:

```bash
cd ~/src/radiasoft/sirepo
npm install karma --save-dev
npm install karma-jasmine --save-dev
npm install karma-phantomjs-launcher
```

To run tests:

```bash
cd ~/src/radiasoft/sirepo
./node_modules/karma/bin/karma start
```


#### Protractor (Angular end-to-end testing)

The tests are located in `tests/protractor`.
[Tutorial on protractor and jasmine.](http://www.protractortest.org/#/tutorial)

As user install node modules:

```bash
cd ~/src/radiasoft/sirepo
npm install protractor
./node_modules/protractor/bin/webdriver-manager update
```

To run tests:

```bash
cd ~/src/radiasoft/sirepo
# Starts server on http://localhost:4444/wd/hub.
DISPLAY=:0 ./node_modules/protractor/bin/webdriver-manager start >& webdriver.log &
# Starts server on 8000 by default
sirepo service http >& http.log &
#
./node_modules/protractor/bin/protractor protractor-conf.js
```

### License

License: http://www.apache.org/licenses/LICENSE-2.0.html

Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
