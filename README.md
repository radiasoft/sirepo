# ![Sirepo](https://github.com/radiasoft/images/blob/master/sirepo/Sirepo_logo.png)

<p align="center">

## Sirepo brings computational science to the cloud.

Develop, run and share your HPC simulations.
</p>

Sirepo brings Clickable Physics(TM) to your desktop and mobile devices.

Run Sirepo directly from [our beta site](https://beta.sirepo.com): beta.sirepo.com.

No signup is required and Sirepo is completely free.

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

## Development

To start developing on vagrant, you should do the following:

```sh
curl radia.run | bash -s vagrant-centos7
vagrant ssh
curl radia.run | bash -s sirepo-dev
source ~/.bashrc
```

Not yet supported, but to install Opal:

```sh
$ curl radia.run | bash -s code pyOPALTools trilinos opal
```

### Full Stack Development

The `sirepo service http` setup is used for basic application development.
However, if you want to test the full stack workflow, you'll need to start
all the support processes and configure your servers.

Set up a few environment variables:

```sh
export PYKERN_PKDEBUG_REDIRECT_LOGGING=1 PYKERN_PKDEBUG_WANT_PID_TIME=1
```

Then run each of the following commands in separate windows:

```sh
sirepo service rabbitmq
SIREPO_CELERY_TASKS_CELERYD_CONCURRENCY=2 SIREPO_MPI_CORES=4 sirepo service celery
SIREPO_SERVER_JOB_QUEUE=Celery sirepo service uwsgi
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
