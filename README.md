# sirepo

# THIS IS PRE-ALPHA SOFTWARE

Sirepo is a scientific application framework, currently for particle accelator codes.
The codes run inside a Python web server.

### Vagrant Install

You can start Sirepo with Vagrant. First create a Vagrantfile:

```bash
cat > Vagrantfile <<'EOF'
Vagrant.configure(2) do |config|
config.vm.box = "radiasoft/sirepo"
config.vm.network "forwarded_port", guest: 8000, host: 8000
end
EOF
```

Boot the machine:

```bash
vagrant up
```

The images is 2.5GB so this will take some time.

You can run Sirepo with a single command:

```bash
vagrant ssh -c '. ~/.bashrc; sirepo service http'
```

Or, if you would like to do development:

```bash
vagrant ssh
cd src/radiasoft/sirepo
sirepo service http
```
