"""test sim_db_file_size

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

max_bytes = 10000


def setup_module(module):
    import os

    os.environ.update(SIREPO_JOB_MAX_MESSAGE_BYTES=str(max_bytes))


def test_max_size(sim_db_file_server):
    from pykern import pkdebug, pkio, pkunit
    from sirepo import sim_data, srunit, util

    stype = srunit.SR_SIM_TYPE_DEFAULT
    c = sim_data.get_class(stype).sim_db_client()

    with pkunit.pkexcept(util.ContentTooLarge):
        c.put(c.LIB_DIR, "content-too-large.txt", (max_bytes + 1) * "a")
