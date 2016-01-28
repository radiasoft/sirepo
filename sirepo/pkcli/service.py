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

from pykern import pkcli
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp

_DEFAULT_DB_SUBDIR = 'run'


def http():
    """Starts Flask server"""
    from sirepo import server
    db_dir = _db_dir()
    with pkio.save_chdir(_run_dir()):
        server.init(db_dir)
        server.app.run(host=cfg.ip, port=cfg.port, debug=1, threaded=True)


def uwsgi():
    """Starts UWSGI server"""
    db_dir =_db_dir()
    run_dir = _run_dir()
    with pkio.save_chdir(run_dir):
        values = dict(pkcollections.map_items(cfg))
        # uwsgi.py must be first, because referenced by uwsgi.yml
        for f in ('uwsgi.py', 'uwsgi.yml'):
            output = run_dir.join(f)
            values[f.replace('.', '_')] = str(output)
            pkjinja.render_resource(f, values, output=output)
        cmd = ['uwsgi', '--yaml=' + values['uwsgi_yml']]
        subprocess.check_call(cmd)


@pkconfig.parse_none
def _cfg_db_dir(value):
    """Config value or root package's parent or cwd with _DEFAULT_SUBDIR"""
    if not value:
        fn = sys.modules[pkinspect.root_package(http)].__file__
        root = py.path.local(py.path.local(py.path.local(fn).dirname).dirname)
        # Check to see if we are in our dev directory. This is a hack,
        # but should be reliable.
        if not root.join('requirements.txt').check():
            # Don't run from an install directory
            root = py.path.local('.')
        value = root.join(_DEFAULT_DB_SUBDIR)
    return value


def _cfg_ip(value):
    try:
        socket.inet_aton(value)
        return value
    except socket.error:
        pkcli.command_error('{}: ip is not a valid IPv4 address', value)



def _cfg_int(lower, upper):
    def wrapper(value):
        v = int(value)
        assert lower <= v <= upper, \
            'value must be from {} to {}'.format(lower, upper)
        return v
    return wrapper


def _db_dir():
    return pkio.mkdir_parent(cfg.db_dir)


def _run_dir():
    return pkio.mkdir_parent(cfg.run_dir)


cfg = pkconfig.init(
    db_dir=(None, _cfg_db_dir, 'where database resides'),
    run_dir=('{SIREPO_PKCLI_SERVICE_DB_DIR}', str, 'where to run the program'),
    port=(8000, _cfg_int(5001, 32767), 'port to listen on'),
    processes=(1, _cfg_int(1, 16), 'how many uwsgi processes to start'),
    # uwsgi got hung up with 1024 threads on a 4 core VM with 4GB
    # so limit to 128, which is probably more than enough with
    # this application.
    threads=(10, _cfg_int(1, 128), 'how many uwsgi threads in each process'),
    ip=('0.0.0.0', _cfg_ip, 'what IP address to open'),
)
