"""Useful function for developers

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcli
from pykern import pkconfig
from pykern import pkio
import sirepo.auth_role
import sirepo.quest
import sirepo.pkcli.roles
import re


_MAIL_DIR = pkio.py_path("~/mail")


def add_admin():
    """Add admin role to all users."""
    _check_dev_mode()
    with sirepo.quest.start() as qcall:
        for u in qcall.auth_db.all_uids():
            sirepo.pkcli.roles.add(u, sirepo.auth_role.ROLE_ADM)


def get_url_from_mail():
    """Get the most recent URL in the mail directory."""
    _check_dev_mode()
    l = pkio.sorted_glob(_MAIL_DIR.join("*"), key="mtime")
    if not l:
        pkcli.command_error(f"No files found in _MAIL_DIR={_MAIL_DIR}")
    return re.search(r"(http://\S+)", pkio.read_text(l[-1])).group(1)


def _check_dev_mode():
    if not pkconfig.in_dev_mode():
        pkcli.command_error("You can only run these commands in dev.")
