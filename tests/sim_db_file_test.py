"""test sim_db_file

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_basic(sim_db_file_server):
    from pykern import pkdebug, pkunit
    from sirepo import sim_data, srunit, simulation_db

    stype = srunit.SR_SIM_TYPE_DEFAULT
    c = sim_data.get_class(stype).sim_db_client()
    pkunit.pkeq(b"xyzzy", c.get(c.LIB_DIR, "hello.txt"))
    c.put(c.LIB_DIR, "hello.txt", "abc")
    pkunit.pkeq(b"abc", c.get(c.LIB_DIR, "hello.txt"))
    c.copy(
        c.uri(c.LIB_DIR, "hello.txt"),
        c.uri(c.LIB_DIR, "bye.txt"),
    )
    pkunit.pkeq(3, c.size(c.LIB_DIR, "bye.txt"))
    pkunit.pkeq(3, c.size(c.LIB_DIR, "hello.txt"))
    c.delete_glob(c.LIB_DIR, "bye")
    with pkunit.pkexcept(FileNotFoundError):
        pkunit.pkeq(3, c.size(c.LIB_DIR, "bye.txt"))
    c.move(
        c.uri(c.LIB_DIR, "hello.txt"),
        c.uri(c.LIB_DIR, "bye.txt"),
    )
    with pkunit.pkexcept(FileNotFoundError):
        pkunit.pkeq(3, c.size(c.LIB_DIR, "hello.txt"))
    pkunit.pkeq(b"abc", c.get(c.LIB_DIR, "bye.txt"))
