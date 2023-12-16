### How to build msgpack.js

```sh
$ mkdir tmp
$ cd tmp
$ node install @msgpack/msgpack browserify
$ echo "global.msgpack = require('@msgpack/msgpack');" > in.js
$ ./node_modules/.bin/browserify in.js -o ~/src/radiasoft/sirepo/sirepo/package_data/static/js/ext/msgpack.js
$ cd ..
$ rm -rf tmp
```
