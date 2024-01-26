"""test sim_db_file

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_basic(sim_db_file_server):
    from pykern import pkdebug, pkunit
    from sirepo import sim_data, srunit

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
        c.size(c.LIB_DIR, "bye.txt")
    c.move(
        c.uri(c.LIB_DIR, "hello.txt"),
        c.uri(c.LIB_DIR, "bye.txt"),
    )
    with pkunit.pkexcept(FileNotFoundError):
        c.size(c.LIB_DIR, "hello.txt")
    pkunit.pkeq(b"abc", c.get(c.LIB_DIR, "bye.txt"))


def test_sim_data(sim_db_file_server):
    from pykern import pkunit
    from sirepo import srunit, sim_data, simulation_db

    with srunit.quest_start() as qcall:
        stype = srunit.SR_SIM_TYPE_DEFAULT
        uid = qcall.auth.logged_in_user()
        sid = simulation_db.iterate_simulation_datafiles(
            stype,
            simulation_db.process_simulation_list,
            None,
            qcall=qcall,
        )[0].simulationId
        c = sim_data.get_class(stype).sim_db_client()
        d = c.read_sim(sid)
        pkunit.pkeq(srunit.SR_SIM_NAME_DEFAULT, d.models.simulation.name)
        d.models.dog.weight = 192000
        n = c.save_sim(d)
        pkunit.pkne(
            n.models.simulation.simulationSerial,
            d.models.simulation.simulationSerial,
        )
        d = c.read_sim(sid)
        pkunit.pkeq(192000, d.models.dog.weight)
        with pkunit.pkexcept(FileNotFoundError):
            c.read_sim("12345678")


def test_save_from_uri(sim_db_file_server):
    from pykern import pkdebug, pkunit
    from sirepo import sim_data, srunit
    import requests

    stype = srunit.SR_SIM_TYPE_DEFAULT
    c = sim_data.get_class(stype).sim_db_client()
    u = "https://www.sirepo.com/static/img/favicon.ico"
    f = c.uri(c.LIB_DIR, "favicon.ico")
    pkunit.pkok(not c.exists(f), "favicon.ico should not exist")
    c.save_from_url(u, f)
    pkunit.pkeq(requests.get(u).content, c.get(f))


def test_uri():
    from pykern import pkunit, pkdebug
    from sirepo import srunit

    def _full(uri, deviance=True):
        r = sim_db_file._uri_parse(f"{job.SIM_DB_FILE_URI}/{uri}", uid)
        if deviance:
            pkunit.pkok(not r, "unexpected res={} uri={} uid={} ", r, uri, uid)
        else:
            pkunit.pkeq(simulation_db.user_path_root().join(uri), r)

    srunit.setup_srdb_root()
    from sirepo import simulation_db, sim_db_file, job

    uid = simulation_db.user_create()
    stype = srunit.SR_SIM_TYPE_DEFAULT
    _full(
        f"{uid}/{stype}/aValidId/flash_exe-SwBZWpYFR-PqFi81T6rQ8g",
        deviance=False,
    )
    _full(f"{uid}/{stype}/invalid/valid-file")
    _full(f"{uid}/invalid/aValidId/valid-file")
    _full(f"notfound/{stype}/aValidId/valid-file")
    _full(f"{uid}/{stype}/aValidId/{'too-long':x>129s}")
    _full(f"{uid}/{stype}/aValidId/.invalid-part")
    _full(f"{uid}/{stype}/aValidId/invalid-part.")
    # too few parts
    _full(f"{uid}/{stype}/aValidId")
