"""test roles

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def setup_module(module):
    from sirepo import srunit
    import os

    srunit.setup_srdb_root()
    os.environ.update(
        SIREPO_AUTH_METHODS="email",
    )
    # init db
    with srunit.quest_start():
        pass


def test_add_plan():
    from pykern import pkunit
    from sirepo.pkcli import admin, roles
    import datetime

    now = datetime.datetime.utcnow()
    u = admin.create_user("a@a.a", "a")
    roles.delete(u, "basic")
    r = roles.list(u)
    pkunit.pkok("basic" not in r, "basic in roles={}", r)
    roles.add_plan(u, "basic", expiration=1)
    r = roles.list_with_expiration(u)
    for x in r:
        if x.role == "basic":
            pkunit.pkok(
                x.expiration >= now + datetime.timedelta(days=1),
                "before 1 day expiration={}",
                x.expiration,
            )
            pkunit.pkok(
                x.expiration < now + datetime.timedelta(days=2),
                "after 2 days expiration={}",
                x.expiration,
            )
            break
    else:
        pkunit.pkfail("no role basic in roles={}", r)
