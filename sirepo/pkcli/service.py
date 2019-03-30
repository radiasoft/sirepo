# -*- coding: utf-8 -*-
"""Runs the server in uwsgi or http modes.

Also supports starting nginx proxy.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from flower import command
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


def celery():
    """Start celery"""
    assert pkconfig.channel_in('dev')
    import celery.bin.celery
    import sirepo.celery_tasks
    run_dir = _run_dir().join('celery').ensure(dir=True)
    with pkio.save_chdir(run_dir):
        celery.bin.celery.main(argv=[
            'celery',
            'worker',
            '--app=sirepo.celery_tasks',
            '--no-color',
            '-Ofair',
            '--queue=' + ','.join(sirepo.celery_tasks.QUEUE_NAMES),
        ])


def flower():
    """Start flower"""
    assert pkconfig.channel_in('dev')
    run_dir = _run_dir().join('flower').ensure(dir=True)
    with pkio.save_chdir(run_dir):
        command.FlowerCommand().execute_from_commandline([
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

    with pkio.save_chdir(_run_dir()):
        use_reloader = pkconfig.channel_in('dev')
        app = server.init(use_reloader=use_reloader)
        # avoid WARNING: Do not use the development server in a production environment.
        app.env = 'development'
        app.run(
            host=cfg.ip,
            port=cfg.port,
            threaded=True,
            use_reloader=use_reloader,
        )


def nginx_proxy():
    """Starts nginx in container.

    Used for development only.
    """
    assert pkconfig.channel_in('dev')
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
        try:
            pksubprocess.check_call_with_signals(cmd)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pkcli.command_error('docker is not installed')


def uwsgi():
    """Starts UWSGI server"""
    run_dir = _run_dir()
    with pkio.save_chdir(run_dir):
        values = dict(pkcollections.map_items(cfg))
        values['logto'] = None if pkconfig.channel_in('dev') else str(run_dir.join('uwsgi.log'))
        # uwsgi.py must be first, because values['uwsgi_py'] referenced by uwsgi.yml
        for f in ('uwsgi.py', 'uwsgi.yml'):
            output = run_dir.join(f)
            values[f.replace('.', '_')] = str(output)
            pkjinja.render_resource(f, values, output=output)
        cmd = ['uwsgi', '--yaml=' + values['uwsgi_yml']]
        pksubprocess.check_call_with_signals(cmd)


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


def _run_dir():
    from sirepo import server

    if not isinstance(cfg.run_dir, type(py.path.local())):
        cfg.run_dir = pkio.mkdir_parent(cfg.run_dir) if cfg.run_dir else server.cfg.db_dir.new()
    return cfg.run_dir


cfg = pkconfig.init(
    ip=('0.0.0.0', _cfg_ip, 'what IP address to open'),
    nginx_proxy_port=(8080, _cfg_int(5001, 32767), 'port on which nginx_proxy listens'),
    port=(8000, _cfg_int(5001, 32767), 'port on which uwsgi or http listens'),
    processes=(1, _cfg_int(1, 16), 'how many uwsgi processes to start'),
    run_dir=(None, str, 'where to run the program (defaults db_dir)'),
    # uwsgi got hung up with 1024 threads on a 4 core VM with 4GB
    # so limit to 128, which is probably more than enough with
    # this application.
    threads=(10, _cfg_int(1, 128), 'how many uwsgi threads in each process'),
)
