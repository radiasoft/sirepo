# -*- coding: utf-8 -*-
"""Runs the server in uwsgi or http modes.

Also supports starting nginx proxy.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkjinja
from pykern import pksubprocess
from pykern.pkdebug import pkdc, pkdexc, pkdp
import json
import os
import py
import socket
import sys


#: Relative directory from current to append to make run_dir
_DEFAULT_DB_SUBDIR = 'run'


def celery():
    """Start celery"""
    import celery.bin.celery
    import sirepo.celery_tasks
    run_dir = _run_dir().join('celery').ensure(dir=True)
    with pkio.save_chdir(run_dir):
        celery.bin.celery.main(argv=[
            'celery',
            'worker',
            '--app=sirepo.celery_tasks',
            '--loglevel=info',
            '--no-color',
            '--queue=' + ','.join(sirepo.celery_tasks.QUEUE_NAMES),
        ])


def flower():
    """Start flower"""
    run_dir = _run_dir().join('flower').ensure(dir=True)
    with pkio.save_chdir(run_dir):
        from flower.command import FlowerCommand
        FlowerCommand().execute_from_commandline([
            'flower',
            '--address=' + cfg.ip,
            '--app=sirepo.celery_tasks',
            '--no-color',
            '--persistent',
        ])


def http():
    """Starts Flask server in http mode.

    Used for development only.
    """
    from sirepo import server
    db_dir = _db_dir()
    with pkio.save_chdir(_run_dir()):
        server.init(db_dir)
        server.app.run(host=cfg.ip, port=cfg.port, debug=1, threaded=True)


def nginx_proxy():
    """Starts nginx in container.

    Used for development only.
    """
    run_dir = _run_dir().join('nginx_proxy').ensure(dir=True)
    with pkio.save_chdir(run_dir):
        f = run_dir.join('default.conf')
        values = dict(pkcollections.map_items(cfg))
        pkjinja.render_resource('nginx_proxy.conf', values, output=f)
        cmd = [
            'docker',
            'run',
            '--net=host',
            '--rm',
            '--volume={}:/etc/nginx/conf.d/default.conf'.format(f),
            'nginx',
        ]
        pksubprocess.check_call_with_signals(cmd)


def rabbitmq():
    assert pkconfig.channel_in('dev')
    run_dir = _run_dir().join('rabbitmq').ensure(dir=True)
    with pkio.save_chdir(run_dir):
        cmd = [
            'docker',
            'run',
            '--env=RABBITMQ_NODE_IP_ADDRESS=' + cfg.ip,
            '--net=host',
            '--rm',
            '--volume={}:/var/lib/rabbitmq'.format(run_dir),
            'rabbitmq:management',
        ]
        pksubprocess.check_call_with_signals(cmd)


def uwsgi():
    """Starts UWSGI server"""
    in_dev = pkconfig.channel_in('dev')
    if in_dev:
        from sirepo import server
        # uwsgi doesn't pass signals right so can't use _Background
        if not issubclass(server.cfg.job_queue, server._Celery):
            pkcli.command_error('uwsgi only works if sirepo.server.cfg.job_queue=_Celery')
    db_dir =_db_dir()
    run_dir = _run_dir()
    with pkio.save_chdir(run_dir):
        values = dict(pkcollections.map_items(cfg))
        values['logto'] = None if in_dev else str(run_dir.join('uwsgi.log'))
        # uwsgi.py must be first, because values['uwsgi_py'] referenced by uwsgi.yml
        for f in ('uwsgi.py', 'uwsgi.yml'):
            output = run_dir.join(f)
            values[f.replace('.', '_')] = str(output)
            pkjinja.render_resource(f, values, output=output)
        cmd = ['uwsgi', '--yaml=' + values['uwsgi_yml']]
        pksubprocess.check_call_with_signals(cmd)


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


def _cfg_emails(value):
    """Parse a list of emails separated by comma, colons, semicolons or spaces.

    Args:
        value (object): if list or tuple, use verbatim; else split
    Returns:
        list: validated emails
    """
    import pyisemail
    try:
        if not isinstance(value, (list, tuple)):
            value = re.split(r'[,;:\s]+', value)
    except Exception:
        pkcli.command_error('{}: invalid email list', value)
    for v in value:
        if not pyisemail.is_email(value):
            pkcli.command_error('{}: invalid email', v)


def _cfg_int(lower, upper):
    def wrapper(value):
        v = int(value)
        assert lower <= v <= upper, \
            'value must be from {} to {}'.format(lower, upper)
        return v
    return wrapper


def _cfg_ip(value):
    try:
        socket.inet_aton(value)
        return value
    except socket.error:
        pkcli.command_error('{}: ip is not a valid IPv4 address', value)


def _db_dir():
    return pkio.mkdir_parent(cfg.db_dir)


def _run_dir():
    return pkio.mkdir_parent(cfg.run_dir)


cfg = pkconfig.init(
    db_dir=(None, _cfg_db_dir, 'where database resides'),
    ip=('0.0.0.0', _cfg_ip, 'what IP address to open'),
    nginx_proxy_port=(8080, _cfg_int(5001, 32767), 'port on which nginx_proxy listens'),
    port=(8000, _cfg_int(5001, 32767), 'port on which uwsgi or http listens'),
    processes=(1, _cfg_int(1, 16), 'how many uwsgi processes to start'),
    run_dir=('{SIREPO_PKCLI_SERVICE_DB_DIR}', str, 'where to run the program'),
    # uwsgi got hung up with 1024 threads on a 4 core VM with 4GB
    # so limit to 128, which is probably more than enough with
    # this application.
    threads=(10, _cfg_int(1, 128), 'how many uwsgi threads in each process'),
)
