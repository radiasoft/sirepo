"""Test pkcli.opal

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_SIM_ID = "autoph01"


def setup_module(module):
    from sirepo import srunit

    srunit.setup_srdb_root()


def test_save_autophase_values():
    from pykern import pkio, pkunit
    from pykern.pkunit import pkeq
    from sirepo import simulation_db, srdb
    from sirepo.pkcli import opal

    pkio.unchecked_remove(srdb.root())
    pkunit.data_dir().join("db").copy(srdb.root())
    opal.save_autophase_values(_SIM_ID)
    d = simulation_db.open_json_file("opal", path=_sim_data_path())
    for e in d.models.elements:
        if e.name == "FINSS_RGUN":
            pkeq(5.1349907881578325, e.lag)
    for c in d.models.commands:
        if c._type == "option":
            pkeq(0, c.autophase)


def _sim_data_path():
    from pykern import pkio
    from sirepo import simulation_db

    return pkio.sorted_glob(
        simulation_db.user_path_root().join("*", "opal", _SIM_ID)
    )[0].join(simulation_db.SIMULATION_DATA_FILE)
