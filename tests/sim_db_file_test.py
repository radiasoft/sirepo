"""test sim_db_file

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_get(sim_db_file_server):
    from pykern import pkdebug, pkunit
    from sirepo import sim_data, srunit, simulation_db

    stype = srunit.SR_SIM_TYPE_DEFAULT
    c = sim_data.get_class(stype).sim_db_client()
    pkunit.pkeq(b"xyzzy", c.get(c.LIB_DIR, "hello.txt"))
