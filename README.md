# ![Sirepo](https://github.com/radiasoft/images/blob/master/sirepo/Sirepo_logo.png)

<p align="center">

## Sirepo brings computational science to the cloud.

</p>

The Sirepo gateway supports physics codes like elegant, Warp, SRW, JSPEC, Zgoubi, and more. With it, you can configure, run, visualize, and share end-to-end HPC physical simulations on your browser. We call this Clickable Physics(TM).

[Try the Sirepo gateway](https://www.sirepo.com). All you need is an email address to access. Sirepo is completely free.

### If you prefer, Sirepo can also be downloaded! :arrow_down:
* [Curl Installer for Mac and Linux](#curl-installer)
* [Manual Install with Docker](#manual-install-with-docker)
* [Development](https://wiki.radiasoft.org/sirepo/wiki/Development)

### Curl Installer

You can use our
[curl installer on your Mac, PC (Cygwin only), or Linux box](https://github.com/radiasoft/download/blob/master/README.md)
as follows:

```bash
$ mkdir sirepo
$ cd sirepo
$ curl https://sirepo.run | bash
```

For this to work, you will need to [install the prerequisites](https://github.com/radiasoft/download/blob/master/README.md#requirements).

[API Documentation is available on Read the Docs.](https://sirepo.readthedocs.io)

### Manual Install with Docker

You can start Sirepo with [Docker](https://www.docker.com/).

If you are running Docker as an ordinary user (recommended), use the following:

```bash
$ docker run --rm -p 8000:8000 -v "$PWD:/sirepo" radiasoft/sirepo
```

Then visit: http://127.0.0.1:8000

The `-v "$PWD:/sirepo"` creates a `db` subdirectory, which is where the database is stored.

### License

License: http://www.apache.org/licenses/LICENSE-2.0.html

Copyright (c) 2015–2025 [RadiaSoft LLC](https://radiasoft.net).  All Rights Reserved.

![RadiaSoft](https://github.com/radiasoft/images/blob/master/corporate/RadiaSoftLogoTransparent.png)
