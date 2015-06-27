# -*- coding: utf-8 -*-
u"""Runs the server in uwsgi or http modes

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import os
import subprocess
import sys

import py

from pykern.pkdebug import pkdc, pkdp
from pykern import pkcli
from pykern import pkinspect
from pykern import pkio
from pykern import pkjinja

_DEFAULT_PORT = 8000
_DEFAULT_SUBDIR = 'run'


def http(port=None, run_dir=None):
    """Starts Flask server"""
    from sirepo import server
    server.init(_run_dir(run_dir))
    server.app.run(host='0.0.0.0', port=_port(port), debug=1)


def uwsgi(port=None, run_dir=None):
    values = {
        'run_dir': _run_dir(str(run_dir)),
        'port': _port(port),
    }
    # uwsgi.py must be first, because referenced by uwsgi.ini
    for f in ('uwsgi.py', 'uwsgi.ini'):
        output = run_dir.join(f)
        values[f.replace('.', '_')] = str(output)
        pkjinja.render_resource(f, values, output=output)
    subprocess.check_call(['uwsgi', '--ini=' + values['uwsgi_ini']])


def _port(port):
    """Returns port or default"""
    try:
        if port:
            res = int(port)
            # http://stackoverflow.com/a/924337
            if res <= 5000 or res >= 32768:
                pkcli.command_error('{}: port is outside 5001 .. 32767', port)
            return res
    except ValueError:
        pkcli.command_error('{}: port is not an int', port)
    return _DEFAULT_PORT


def _run_dir(run_dir):
    """Returns root package's parent or cwd with _DEFAULT_SUBDIR"""
    if not run_dir:
        fn = sys.modules[pkinspect.root_package(http)].__file__
        root = py.path.local(py.path.local(fn).dirname).dirname
        if root in sys.path:
            root = '.'
        run_dir = py.path.local(root).join(_DEFAULT_SUBDIR)
    pkdp(run_dir)
    return pkio.mkdir_parent(run_dir)
