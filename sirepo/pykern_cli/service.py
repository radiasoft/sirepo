# -*- coding: utf-8 -*-
"""Runs the server in uwsgi or http modes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import json
import os
import socket
import subprocess
import sys

import py

from pykern.pkdebug import pkdc, pkdp
from pykern import pkcli
from pykern import pkinspect
from pykern import pkio
from pykern import pkjinja

import sirepo.template.srw
import sirepo.template.warp

_DEFAULT_DB_SUBDIR = 'run'
_CFG = {
    'db_dir': None,
     # http://stackoverflow.com/a/924337
    'port': [8000, 5001, 32767],
    'processes': [1, 1, 16],
    'run_dir': None,
    # uwsgi got hung up with 1024 threads on a 4 core VM with 4GB
    # so limit to 128, which is probably more than enough with
    # this application.
    'threads': [10, 1, 128],
    'ip': '0.0.0.0',
}


def fixup_json_datafile(app_name, path):
    template = None
    if app_name == 'srw':
        template = sirepo.template.srw
    elif app_name == 'warp':
        template = sirepo.template.warp
    else:
        return 'invalid app_name: {}'.format(app_name)
    with open(str(path)) as f:
        data = json.load(f)
    template.fixup_old_data(data)
    with open(str(path), 'w') as f:
        json.dump(data, f)


def fixup_json_datafiles(app_name):
    """Apply schema fixups for application datafiles. app_name: (srw|warp)"""
    files = pkio.walk_tree('.', '/' + app_name + '/[^\/]+/sirepo-data.json')
    if not len(files):
        return 'no files found for {}'.format(app_name)
    ask = raw_input('apply fixups to {} files? (y|n) '.format(len(files)))
    if not (ask and ask == 'y'):
        return '** aborting data fixup **'
    for path in files:
        res = fixup_json_datafile(app_name, str(path))
        if res:
            pkdp('{}: {}', path, res)
    return 'applied fixups to {} files.'.format(len(files))


def http():
    """Starts Flask server"""
    from sirepo import server
    db_dir = _db_dir()
    with pkio.save_chdir(_run_dir(db_dir), mkdir=True):
        server.init(db_dir)
        server.app.run(host=_ip(), port=_int('port'), debug=1, threaded=True)


def uwsgi():
    """Starts UWSGI server"""
    db_dir =_db_dir()
    run_dir = _run_dir(db_dir)
    with pkio.save_chdir(run_dir, mkdir=True):
        values = {
            'db_dir': db_dir,
            'ip': _ip(),
            'port': _int('port'),
            'processes': _int('processes'),
            'run_dir': run_dir,
            'threads': _int('threads'),
        }
        # uwsgi.py must be first, because referenced by uwsgi.yml
        for f in ('uwsgi.py', 'uwsgi.yml'):
            output = run_dir.join(f)
            values[f.replace('.', '_')] = str(output)
            pkjinja.render_resource(f, values, output=output)
        cmd = ['uwsgi', '--yaml=' + values['uwsgi_yml']]
        subprocess.check_call(cmd)


def _db_dir():
    """Config value or root package's parent or cwd with _DEFAULT_SUBDIR"""
    value = _env('db_dir')
    if not value:
        fn = sys.modules[pkinspect.root_package(http)].__file__
        root = py.path.local(py.path.local(py.path.local(fn).dirname).dirname)
        # Check to see if we are in our dev directory. This is a hack,
        # but should be reliable.
        if not root.join('requirements.txt').check():
            # Don't run from an install directory
            root = py.path.local('.')
        value = root.join(_DEFAULT_DB_SUBDIR)
    return pkio.mkdir_parent(value)


def _env(name, default=None):
    default = _CFG[name] if default is None else default
    default = default[0] if isinstance(default, list) else default
    return os.getenv('SIREPO_PKCLI_SERVICE_' + name.upper(), default)


def _int(name):
    value = _env(name)
    try:
        res = int(value)
        d = _CFG[name]
        if not d[1] <= res <= d[2]:
            pkcli.command_error('{}: {} is outside {} .. {}', value, name, d[1], d[2])
        return res
    except ValueError:
        pkcli.command_error('{}: {} is not an int', value, name)


def _ip():
    try:
        value = _env('ip')
        socket.inet_aton(value)
        return value
    except socket.error:
        pkcli.command_error('{}: ip is not a valid IPv4 address', value)


def _run_dir(db_dir):
    """Returns execution directory"""
    return pkio.mkdir_parent(_env('run_dir', db_dir))
