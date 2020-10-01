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
from pykern import pkio
from pykern import pkjinja
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import contextlib
import os
import py
import re
import signal
import socket
import subprocess
import time

__cfg = None


def flask():
    from sirepo import server
    import sirepo.pkcli.setup_dev

    with pkio.save_chdir(_run_dir()):
        sirepo.pkcli.setup_dev.default_command()
        # above will throw better assertion, but just in case
        assert pkconfig.channel_in('dev')
        app = server.init(use_reloader=_cfg().use_reloader)
        # avoid WARNING: Do not use the development server in a production environment.
        app.env = 'development'
        import werkzeug.serving
        werkzeug.serving.click = None
        app.run(
            host=_cfg().ip,
            port=_cfg().port,
            threaded=True,
            use_reloader=_cfg().use_reloader,
        )


def http():
    """Starts the Flask server and job_supervisor.

    Used for development only.
    """
    e = PKDict(os.environ)
    e.SIREPO_JOB_DRIVER_MODULES = 'local'
    _start_processes(
        [['sirepo'] + c for c in [
            ['service', 'flask'], ['job_supervisor'],
        ]],
        e,
    )

def jupyterhub():
    assert pkconfig.channel_in('dev')
    try:
        import jupyterhub
    except ImportError:
        raise ImportError('jupyterhub not installed. run `pip install jupyterhub`')
    import sirepo.sim_api.jupyterhublogin
    import sirepo.server

    sirepo.server.init()
    f = _run_dir().join('jupyterhub').ensure(dir=True).join('conf.py')
    pkjinja.render_resource(
        'jupyterhub_conf.py',
        PKDict(_cfg()).pkupdate(**sirepo.sim_api.jupyterhublogin.cfg),
        output=f,
    )
    _start_processes(
       [
           ['sirepo', 'service', 'nginx_proxy', '--jupyterhub'],
           ['sirepo', 'service', 'uwsgi'],
           ['sirepo', 'job_supervisor'],
           ['jupyterhub', '-f', str(f)],
        ],
        env=PKDict(os.environ).pkupdate(
            SIREPO_AUTH_METHODS='github:email',
            SIREPO_AUTH_GITHUB_METHOD_VISIBLE='',
        ),
    )


def nginx_proxy(jupyterhub=False):
    """Starts nginx in container.

    Used for development only.
    """
    assert pkconfig.channel_in('dev')
    run_dir = _run_dir().join('nginx_proxy').ensure(dir=True)
    with pkio.save_chdir(run_dir) as d:
        f = run_dir.join('default.conf')
        c = PKDict(_cfg()).pkupdate(run_dir=str(d))
        if jupyterhub:
            import sirepo.sim_api.jupyterhublogin
            import sirepo.server

            sirepo.server.init()
            c.pkupdate(
                jupyterhub_root=sirepo.sim_api.jupyterhublogin.cfg.uri_root,
            )
        pkjinja.render_resource(
            'nginx_proxy.conf',
            c,
            output=f,
        )
        cmd = [
            'nginx',
            '-c',
            str(f),
        ]
        pksubprocess.check_call_with_signals(cmd)


def uwsgi():
    """Starts UWSGI server"""
    run_dir = _run_dir()
    with pkio.save_chdir(run_dir):
        values = _cfg().copy()
        values['logto'] = None if pkconfig.channel_in('dev') else str(run_dir.join('uwsgi.log'))
        # uwsgi.py must be first, because values['uwsgi_py'] referenced by uwsgi.yml
        for f in ('uwsgi.py', 'uwsgi.yml'):
            output = run_dir.join(f)
            values[f.replace('.', '_')] = str(output)
            pkjinja.render_resource(f, values, output=output)
        cmd = ['uwsgi', '--yaml=' + values['uwsgi_yml']]
        pksubprocess.check_call_with_signals(cmd)


def _cfg():
    global __cfg
    if not __cfg:
        __cfg = pkconfig.init(
            ip=('0.0.0.0', _cfg_ip, 'what IP address to open'),
            jupyterhub_port=(8005, _cfg_port, 'port on which jupyterhub listens'),
            nginx_proxy_port=(8080, _cfg_port, 'port on which nginx_proxy listens'),
            port=(8000, _cfg_port, 'port on which uwsgi or http listens'),
            processes=(1, _cfg_int(1, 16), 'how many uwsgi processes to start'),
            run_dir=(None, str, 'where to run the program (defaults db_dir)'),
            # uwsgi got hung up with 1024 threads on a 4 core VM with 4GB
            # so limit to 128, which is probably more than enough with
            # this application.
            threads=(10, _cfg_int(1, 128), 'how many uwsgi threads in each process'),
            use_reloader=(pkconfig.channel_in('dev'), bool, 'use the Flask reloader'),
        )
    return __cfg


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


def _cfg_port(value):
    return _cfg_int(5001, 32767)(value)


def _run_dir():
    from sirepo import server
    import sirepo.srdb

    if not isinstance(_cfg().run_dir, type(py.path.local())):
        _cfg().run_dir = pkio.mkdir_parent(_cfg().run_dir) if _cfg().run_dir else sirepo.srdb.root()
    return _cfg().run_dir


def _start_processes(cmds, env=None):
    @contextlib.contextmanager
    def _handle_signals(signums):
        o = [(x, signal.getsignal(x)) for x in signums]
        try:
            [signal.signal(x[0], _kill) for x in o]
            yield
        finally:
            [signal.signal(x[0], x[1]) for x in o]

    def _kill(*args):
        for p in processes:
            try:
                p.terminate()
                p.wait(1)
            except (ProcessLookupError, ChildProcessError):
                continue
            except subprocess.TimeoutExpired:
                p.kill()

    def _start(cmd):
        processes.append(subprocess.Popen(
            cmd,
            cwd=str(_run_dir()),
            env=env,
        ))
    env = env if env else os.environ
    processes = []
    with pkio.save_chdir(_run_dir()), \
        _handle_signals((signal.SIGINT, signal.SIGTERM)):
        try:
            for c in cmds:
                # Avoid race condition on creating auth db
                time.sleep(.3)
                _start(['pyenv', 'exec'] + c)
            p, _ = os.wait()
        except ChildProcessError:
            pass
        finally:
            _kill()
