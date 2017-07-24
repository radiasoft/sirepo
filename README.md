# ![Sirepo](https://github.com/radiasoft/images/blob/master/sirepo/Sirepo_logo.png)

<p align="center">

## Sirepo brings computational science to the cloud.

Develop, run and share your HPC simulations.
</p>

Sirepo brings Clickable Physics(TM) to your desktop and mobile devices.

Run Sirepo directly from [our beta site](https://beta.sirepo.com): beta.sirepo.com.

No signup is required and Sirepo is completely free.

# .

### If you prefer, Sirepo can also be downloaded! :arrow_down:
1. Curl Installer
2. Install with Docker
3. Install with Vagrant

#### Curl Installer
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

#### Manual Install with Docker

You can start Sirepo with [Docker](https://www.docker.com/).

If you are running Docker as an ordinary user (recommended), use the following:

```bash
$ docker run -p 8000:8000 -v "$PWD:/sirepo" radiasoft/sirepo
```

The `/radia-run` command ensures the guest's user can read/write files from the
current directory, which is where the database and other files will be stored.


Then visit the following link:

[http://localhost:8000/light](http://localhost:8000/light)

#### Manual Install with Vagrant

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

The image is 2.5GB so this will take some time to start.

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


##### Sharing Folder with Vagrant VM

Note that if you want to transfer files to the virtual machine,
you'll need to install the
[vagrant-vbguest plugin](https://github.com/dotless-de/vagrant-vbguest)
and remove the following line from the `Vagrantfile`:

```text
config.vm.synced_folder ".", "/vagrant", disabled: true
```

#### Angular Testing

In order to test, you need to install Xvfb, nodejs (v4+), and google-chrome.

[Extensive tutorial on Angular Testing from 2013, which gives advice on jasmine testing, but uses obsolete scenario runner.](http://www.yearofmoo.com/2013/01/full-spectrum-testing-with-angularjs-and-karma.html)

[Advice on how to test better](http://www.yearofmoo.com/2013/09/advanced-testing-and-debugging-in-angularjs.html#writing-efficient-tests)

Install node globally as root:

```bash
curl -s -S -L https://rpm.nodesource.com/setup_4.x | bash
yum install -y nodejs
```

Install Xvfb globally as root. It runs as vagrant:

```bash
yum install -y xorg-x11-server-Xvfb xorg-x11-server-utils
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

##### Karma (Angular unit testing)

The tests are located in `tests/karma`.
[Tutorial on karma and jasmine.](https://daveceddia.com/testing-angular-part-1-karma-setup/)

As user install node modules:

```bash
cd ~/src/radiasoft/sirepo
npm install --save-dev karma
npm install --save-dev karma-jasmine
npm install --save-dev karma-phantomjs-launcher
```

To run tests:

```bash
cd ~/src/radiasoft/sirepo
./node_modules/karma/bin/karma start karma-conf.js
```

##### Protractor (Angular end-to-end testing)

The tests are located in `tests/protractor`.
[Tutorial on protractor and jasmine.](http://www.protractortest.org/#/tutorial)

As user install node modules and Chrome:

```bash
cd ~/src/radiasoft/sirepo
npm install --save-dev protractor
npm install --save-dev protractor-snapshot
npm install --save-dev protractor-console
npm install --save-dev protractor-console-plugin
./node_modules/protractor/bin/webdriver-manager update
yum update -y google-chrome-stable
```

Verify the X11 server is running:

```bash
DISPLAY=:0 xset q > /dev/null && echo OK
```

To run tests:

```bash
cd ~/src/radiasoft/sirepo
# Starts server on http://localhost:4444/wd/hub
DISPLAY=:0 ./node_modules/protractor/bin/webdriver-manager start --chrome_logs="$PWD/chrome.log" >& webdriver.log &
# Default is 8000
SIREPO_PKCLI_SERVICE_PORT=8000 sirepo service http >& http.log &
# You don't need to pass uri as it is set to 8000 by default, but clearer
./node_modules/protractor/bin/protractor --params.uri=http://localhost:8000 protractor-conf.js
```

Output will look like:

```bash
./node_modules/protractor/bin/protractor protractor-conf.js
[16:20:30] I/hosted - Using the selenium server at http://localhost:4444/wd/hub
[16:20:30] I/launcher - Running 1 instances of WebDriver
Started
.


1 spec, 0 failures
Finished in 6.88 seconds
[16:20:40] I/launcher - 0 instance(s) of WebDriver still running
[16:20:40] I/launcher - chrome #01 passed
```

If you would like to see what the browser (webdriver) is doing, you
must have X11 running, and start the webdriver this way:

```bash
./node_modules/protractor/bin/webdriver-manager start >& webdriver.log &
```

This will use the `$DISPLAY` forwarded through your ssh session via
Vagrant.

#### Full Stack Development

The `sirepo service http` setup is used for basic application development.
However, if you want to test the full stack workflow, you'll need to start
all the support processes and configure your servers.

Set up a few environment variables:

```sh
export SIREPO_SERVER_JOB_QUEUE=Celery
export SIREPO_MPI_CORES=4
export PYKERN_PKDEBUG_REDIRECT_LOGGING=1
export PYKERN_PKDEBUG_WANT_PID_TIME=1
export SIREPO_CELERY_TASKS_CELERYD_CONCURRENCY=2
```

Then run each of the following commands in separate windows:

```sh
sirepo service rabbitmq
sirepo service celery
sirepo service uwsgi
sirepo service nginx_proxy
sirepo service flower
```

[nginx](http://nginx.org) will listen on port 8080 so you can browse
Sirepo at [http://localhost:8080](http://localhost:8080). The
middle tier [uwsgi](http://uwsgi-docs.readthedocs.io) server
will start on port 8000.

The last process starts [Flower](http://flower.readthedocs.io),
which allows you to monitor [Celery](http://www.celeryproject.org).
You can visit [http://localhost:5555](http://localhost:5555)
to see the workers, tasks, processes, queues, etc.

You can also visit
[RabbitMQ's Management Plugin](https://www.rabbitmq.com/management.html)
on this URL:
[http://localhost:15672](http://localhost:15672).

### License

License: http://www.apache.org/licenses/LICENSE-2.0.html

Copyright (c) 2015-2016 [RadiaSoft LLC](http://radiasoft.net/open-source).  All Rights Reserved.

![RadiaSoft](https://github.com/radiasoft/images/blob/master/corporate/RadiaSoftLogoTransparent.png)
