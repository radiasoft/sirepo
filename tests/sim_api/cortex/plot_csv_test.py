"""Test cortex plot data stored in csv files, and the migration from the db

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_MODEL = "wcllSlabAnimation"

# plot_legend and plot_point as created before plot data moved to csv files
_PLOT_LEGEND_SQL = (
    "CREATE TABLE plot_legend (plot_id BIGINT NOT NULL, dim INTEGER NOT NULL,"
    + " label VARCHAR(100) NOT NULL, PRIMARY KEY (plot_id, dim))"
)

_PLOT_POINT_SQL = (
    "CREATE TABLE plot_point (plot_id BIGINT NOT NULL, dim INTEGER NOT NULL,"
    + " idx INTEGER NOT NULL, point FLOAT NOT NULL, PRIMARY KEY (plot_id, dim, idx))"
)

_UID = "unittst1"


def setup_module(module):
    from sirepo import srunit

    srunit.setup_srdb_root()


def test_1_drop_plot_tables():
    """Old db with plot_point and plot_legend rows migrates to csv files"""
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    from sirepo.sim_api.cortex import material_db
    import sirepo.template.cortex

    # old tables must exist before init_module so the schema includes them
    _sql(_PLOT_LEGEND_SQL, _PLOT_POINT_SQL)
    material_db.init_module()
    _material(1001)
    _old_plot(1001, 6001, "dpa_OB_1_b6", ["Armor", "VV"])
    # a plot which already has a csv, with a different legend than the db
    _old_plot(1001, 6002, "h1_OB_1_b6", ["Armor"])
    f = material_db.plot_csv_path(1001, _MODEL, "h1_OB_1_b6")
    pkio.mkdir_parent_only(f)
    pkio.write_text(
        f,
        sirepo.template.cortex.csv_from_plot(_plotdef("h1_OB_1_b6", ["First wall"])),
    )
    c = pkio.read_text(f)
    material_db.drop_plot_tables()
    pkunit.pkeq(["plot"], _plot_tables())
    pkunit.pkeq(c, pkio.read_text(f))
    _assert_summary(
        1001, PKDict(dpa_OB_1_b6=["Armor", "VV"], h1_OB_1_b6=["First wall"])
    )


def test_2_partial_migration():
    """plot_point already dropped, so only plot_legend is left to drop"""
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo.sim_api.cortex import material_db

    _sql(_PLOT_LEGEND_SQL, "INSERT INTO plot_legend VALUES (6001, 0, '')")
    material_db.drop_plot_tables()
    pkunit.pkeq(["plot"], _plot_tables())
    _assert_summary(
        1001, PKDict(dpa_OB_1_b6=["Armor", "VV"], h1_OB_1_b6=["First wall"])
    )


def test_3_plot_point_without_legend():
    """plot_point without plot_legend can't be migrated, so nothing is dropped"""
    from pykern import pkunit
    from sirepo.sim_api.cortex import material_db

    _sql(_PLOT_POINT_SQL)
    with pkunit.pkexcept("plot_point without plot_legend"):
        material_db.drop_plot_tables()
    pkunit.pkeq(["plot", "plot_point"], _plot_tables())
    _sql("DROP TABLE plot_point")


def test_4_update_and_load_summary():
    """A new summary's plots round trip through their csv files"""
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    from sirepo.sim_api.cortex import material_db
    import datetime
    import sirepo.template.cortex

    _material(2001)
    p = _plotdef("dpa_OB_1_b6", ["Armor", "First wall", "VV"]).pkupdate(
        material_id=2001
    )
    material_db.update_sim_summary(
        PKDict(
            material_id=2001,
            model=_MODEL,
            version="1.03",
            completed=datetime.datetime.now(),
            plots=[p],
            values=[],
        ),
        _UID,
    )
    # written after update_sim_summary, as in sim_api.cortex.check_for_sim_summary
    f = material_db.plot_csv_path(2001, _MODEL, p.stat)
    pkio.mkdir_parent_only(f)
    pkio.atomic_write(f, sirepo.template.cortex.csv_from_plot(p))
    _assert_summary(2001, PKDict(dpa_OB_1_b6=["Armor", "First wall", "VV"]))
    pkunit.pkok(
        material_db.delete_material(material_id=2001, uid=_UID),
        "delete_material material_id=2001 failed",
    )
    pkunit.pkeq([], _sql("SELECT plot_id FROM plot WHERE material_id = 2001"))


def _assert_summary(material_id, expect):
    """load_summary returns each plot's points and legend from its csv"""
    from pykern import pkunit
    from sirepo.sim_api.cortex import material_db

    r = material_db.load_summary(material_id, False, _UID).plots
    pkunit.pkeq(sorted(expect.keys()), sorted(x.meta.stat for x in r))
    for x in r:
        e = _points(expect[x.meta.stat])
        pkunit.pkeq(e[0], x.x_points)
        pkunit.pkeq(e[1:], [y.points for y in x.plots])
        pkunit.pkeq(expect[x.meta.stat], [y.label for y in x.plots])


def _material(material_id):
    _sql(
        "INSERT INTO material (material_id, uid, created, material_name,"
        + " density_g_cm3, is_atom_pct, is_plasma_facing)"
        + f" VALUES ({material_id}, '{_UID}', '2026-10-30 00:00:00.000000',"
        + f" 'material {material_id}', 7.8, 0, 0)"
    )


def _old_plot(material_id, plot_id, stat, labels):
    """Plot row with its points and legend in the old tables"""
    _sql(
        "INSERT INTO plot VALUES"
        + f" ({plot_id}, {material_id}, '{_MODEL}', '{stat}',"
        + " 'title', 'x [cm]', 'y', 'linear')",
        *(
            f"INSERT INTO plot_legend VALUES ({plot_id}, {d}, '{l}')"
            for d, l in enumerate([""] + labels)
        ),
        *(
            f"INSERT INTO plot_point VALUES ({plot_id}, {d}, {i}, {v})"
            for d, p in enumerate(_points(labels))
            for i, v in enumerate(p)
        ),
    )


def _plot_tables():
    return [
        r[0]
        for r in _sql(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
            + " AND name LIKE 'plot%' ORDER BY name"
        )
    ]


def _plotdef(stat, labels):
    """Plot as built by template.cortex._plot_from_file"""
    from pykern.pkcollections import PKDict

    return PKDict(
        title="title",
        xlabel="x [cm]",
        ylabel="y",
        plot_type="linear",
        model=_MODEL,
        stat=stat,
        legend=[""] + labels,
        points=_points(labels),
    )


def _points(labels):
    """x and one y dimension per label"""
    return [[0.0, 1.5, 3.0]] + [
        [float(d), d + 0.25, d * 1e-3] for d in range(1, len(labels) + 1)
    ]


def _sql(*statements):
    """Run statements on the cortex db, returns the last one's rows"""
    from sirepo.sim_api.cortex import material_db
    import sqlite3

    c = sqlite3.connect(str(material_db._path()))
    try:
        for s in statements:
            rv = c.execute(s).fetchall()
        c.commit()
        return rv
    finally:
        c.close()
