"""Runs API server and job supervisor

Also supports starting nginx proxy.

:copyright: Copyright (c) 2015-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcli
from pykern import pkconfig
from pykern import pkio
from pykern import pkjinja
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdp, pkdlog
import contextlib
import os
import psutil
import py
import pyisemail
import re
import signal
import sirepo.const
import sirepo.feature_config
import sirepo.modules
import sirepo.pkcli.setup_dev
import sirepo.sim_api.jupyterhublogin
import sirepo.srdb
import sirepo.template
import sirepo.util
import socket
import subprocess
import time


__cfg = None


def http():
    """Starts the server and job_supervisor.

    Used for development only.
    """

    processes = []

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
                for c in list(psutil.Process(p.pid).children(recursive=True)):
                    _safe_kill_process(c)
            except Exception:
                # need to ignore exceptions while converting process children
                # to a list so that the parent is still terminated
                pass
            _safe_kill_process(p)

    def _safe_kill_process(proc):
        try:
            proc.terminate()
            proc.wait(1)
        except (
            ProcessLookupError,
            ChildProcessError,
            psutil.NoSuchProcess,
        ):
            pass
        except (psutil.TimeoutExpired, subprocess.TimeoutExpired):
            proc.kill()

    def _start(service, extra_environ, cwd=".", want_prefix=True):
        if not want_prefix:
            prefix = ()
        else:
            if sirepo.feature_config.cfg().trust_sh_env:
                prefix = ("sirepo",)
            else:
                prefix = ("pyenv", "exec", "sirepo")
        processes.append(
            subprocess.Popen(
                prefix + service,
                cwd=str(_run_dir().join(cwd)),
                env=PKDict(os.environ).pkupdate(extra_environ),
            )
        )

    def _start_vue_server():
        e = PKDict()
        if _cfg().vue_port:
            _VUE_DIR = "../vue"
            p = pkio.py_path(f"{_VUE_DIR}/node_modules")
            if not p.exists():
                pkdlog("Need to install vue (takes a few seconds)...")
                os.system(f"cd '{p.dirname}' && npm install")
            _start(
                ("npm", "run", "dev"),
                cwd=_VUE_DIR,
                want_prefix=False,
                extra_environ=PKDict(PORT=str(_cfg().vue_port)),
            )
            e.SIREPO_SERVER_VUE_SERVER = f"http://127.0.0.1:{_cfg().vue_port}/"
        return e

    assert pkconfig.in_dev_mode()
    try:
        with pkio.save_chdir(_run_dir()), _handle_signals(
            (signal.SIGINT, signal.SIGTERM)
        ):
            _start(("service", "server"), extra_environ=_start_vue_server())
            # Avoid race condition on creating auth db
            # Not asyncio.sleep: at server startup
            time.sleep(0.3)
            _start(
                ("job_supervisor",),
                extra_environ=PKDict(SIREPO_JOB_DRIVER_MODULES="local"),
            )
            p, _ = os.wait()
    except ChildProcessError:
        pass
    finally:
        _kill()


def jupyterhub():
    assert pkconfig.in_dev_mode()
    sirepo.template.assert_sim_type("jupyterhublogin")
    with pkio.save_chdir(_run_dir().join("jupyterhub").ensure(dir=True)) as d:
        f = d.join("conf.py")
        pkjinja.render_resource(
            "jupyterhub_conf.py",
            PKDict(_cfg()).pkupdate(
                # POSIT: Running with nginx and server
                sirepo_uri=f"http://{socket.getfqdn()}:{_cfg().nginx_proxy_port}",
                jupyterhub_debug=sirepo.feature_config.cfg().debug_mode,
                **sirepo.sim_api.jupyterhublogin.cfg(),
            ),
            output=f,
        )
        pksubprocess.check_call_with_signals(("jupyterhub", "-f", str(f)))


def nginx_proxy():
    """Starts nginx in container.

    Used for development only.
    """
    import sirepo.template

    assert pkconfig.in_dev_mode()
    run_dir = _run_dir().join("nginx_proxy").ensure(dir=True)
    with pkio.save_chdir(run_dir) as d:
        f = run_dir.join("default.conf")
        c = PKDict(_cfg()).pkupdate(run_dir=str(d))
        if sirepo.util.is_jupyter_enabled():
            c.pkupdate(
                jupyterhub_root=sirepo.sim_api.jupyterhublogin.cfg().uri_root,
            )
        pkjinja.render_resource("nginx_proxy.conf", c, output=f)
        cmd = [
            "nginx",
            "-c",
            str(f),
        ]
        pksubprocess.check_call_with_signals(cmd)


def server():
    tornado()


def tornado():
    def _is_primary(**kwargs):
        """By default always primary, or if matches port"""
        p = _cfg().tornado_primary_port
        kwargs["is_primary"] = p is None or p == kwargs["port"]
        return kwargs

    with pkio.save_chdir(_run_dir()) as r:
        d = pkconfig.in_dev_mode()
        if d:
            sirepo.pkcli.setup_dev.default_command()
            if _cfg().use_reloader:
                import tornado.autoreload

                for f in sirepo.util.files_to_watch_for_reload("json", "py"):
                    tornado.autoreload.watch(f)
        pkdlog("ip={} port={}", _cfg().ip, _cfg().port)
        sirepo.modules.import_and_init("sirepo.uri_router").start_tornado(
            **_is_primary(
                debug=sirepo.feature_config.cfg().debug_mode,
                ip=_cfg().ip,
                port=_cfg().port,
            ),
        )


def _cfg():
    global __cfg
    if not __cfg:
        __cfg = pkconfig.init(
            ip=("0.0.0.0", _cfg_ip, "what IP address to open"),
            jupyterhub_port=(
                sirepo.const.PORT_DEFAULTS.jupyterhub,
                _cfg_port,
                "port on which jupyterhub listens",
            ),
            nginx_proxy_port=(
                sirepo.const.PORT_DEFAULTS.nginx_proxy,
                _cfg_port,
                "port on which nginx_proxy listens",
            ),
            port=(
                sirepo.const.PORT_DEFAULTS.http,
                _cfg_port,
                "port on which http listens",
            ),
            run_dir=(None, str, "where to run the program (defaults db_dir)"),
            tornado_primary_port=(
                None,
                int,
                "for multi-instance tornado, port of controlling api server",
            ),
            use_reloader=(pkconfig.in_dev_mode(), bool, "use the server reloader"),
            vue_port=(
                (
                    sirepo.const.PORT_DEFAULTS.vue
                    if sirepo.feature_config.cfg().vue_sim_types
                    else None
                ),
                _cfg_port,
                "port on which vue listens",
            ),
        )
    return __cfg


def _cfg_emails(value):
    """Parse a list of emails separated by comma, colons, semicolons or spaces.

    Args:
        value (object): if list or tuple, use verbatim; else split
    Returns:
        list: validated emails
    """
    try:
        if not isinstance(value, (list, tuple)):
            value = re.split(r"[,;:\s]+", value)
    except Exception:
        pkcli.command_error("{}: invalid email list", value)
    for v in value:
        if not pyisemail.is_email(value):
            pkcli.command_error("{}: invalid email", v)


def _cfg_int(lower, upper):
    def wrapper(value):
        v = int(value)
        assert lower <= v <= upper, "value must be from {} to {}".format(lower, upper)
        return v

    return wrapper


def _cfg_ip(value):
    try:
        socket.inet_aton(value)
        return value
    except socket.error:
        pkcli.command_error("{}: ip is not a valid IPv4 address", value)


def _cfg_port(value):
    if not value:
        return None
    return _cfg_int(sirepo.const.PORT_MIN, sirepo.const.PORT_MAX)(value)


def _run_dir():
    if not isinstance(_cfg().run_dir, type(py.path.local())):
        _cfg().run_dir = (
            pkio.mkdir_parent(_cfg().run_dir) if _cfg().run_dir else sirepo.srdb.root()
        )
    return _cfg().run_dir
