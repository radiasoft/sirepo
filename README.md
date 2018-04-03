# ![Sirepo](https://github.com/radiasoft/images/blob/master/sirepo/Sirepo_logo.png)

<p align="center">

## Sirepo brings computational science to the cloud.

Develop, run and share your HPC simulations.
</p>

Sirepo brings Clickable Physics(TM) to your desktop and mobile devices.

[Try our public Sirepo server](http://sirepo.com).

No signup is required and Sirepo is completely free.

## If you prefer, Sirepo can also be downloaded! :arrow_down:
1. [Curl Installer for Mac and Linux](#curl-installer)
2. [Manual Install with Docker](#manual-install-with-docker)
3. [Development](#development)

## Curl Installer
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

## Manual Install with Docker

You can start Sirepo with [Docker](https://www.docker.com/).

If you are running Docker as an ordinary user (recommended), use the following:

```bash
$ docker run --rm -p 8000:8000 -v "$PWD:/sirepo" radiasoft/sirepo
```

Then visit: http://127.0.0.1:8000

The `-v "$PWD:/sirepo"` creates a `db` subdirectory, which is where the database is stored.

## Development

We use [vagrant](https://www.vagrantup.com) to develop Sirepo. To install a virtual machine with most of the codes, do this:

```sh
mkdir v
cd v
curl radia.run | bash -s vagrant-sirepo-dev
vagrant ssh
```

The host defaults to `v.radia.run` (ip 10.10.10.10). You can also specify one after `vagrant-sirepo-dev`, e.g.

```sh
curl radia.run | bash -s vagrant-sirepo-dev my-host.example.com 1.2.3.4
```

Not all the codes install automatically.  You can install OPAL inside the Vagrant instance with:

```sh
$ curl radia.run | bash -s code pyOPALTools trilinos opal
```

## Full Stack Development

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

# License

License: http://www.apache.org/licenses/LICENSE-2.0.html

Copyright (c) 2015-2016 [RadiaSoft LLC](http://radiasoft.net/open-source).  All Rights Reserved.

![RadiaSoft](https://github.com/radiasoft/images/blob/master/corporate/RadiaSoftLogoTransparent.png)
