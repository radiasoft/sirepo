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

[[http://localhost:8000/light]]

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

[[http://localhost:8000/light]]

#### Sharing Folder with Vagrant VM

Note that if you want to transfer files to the virtual machine,
you'll need to install the
[vagrant-vbguest plugin](https://github.com/dotless-de/vagrant-vbguest)
and remove the following line from the `Vagrantfile`:

```text
config.vm.synced_folder ".", "/vagrant", disabled: true
```

#### License

License: http://www.apache.org/licenses/LICENSE-2.0.html

Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
