"""Cortex db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.sql_db
import sirepo.srdb
import sirepo.template.cortex
import sirepo.util
import sqlalchemy
import sqlalchemy.exc

_BASE = "cortex_material.sqlite3"

_meta = None


class Error(RuntimeError):
    pass


def db_upgrade():
    if not _path().exists():
        # for tests, db may not exist to upgrade
        return
    with _session() as s:
        if "stat" in [
            v["name"] for v in sqlalchemy.inspect(s.meta._engine).get_columns("plot")
        ]:
            return
        s.execute(f"ALTER TABLE plot ADD COLUMN stat VARCHAR(100)")
        s.execute(f"CREATE INDEX ix_plot_stat ON plot (stat)")


def delete_material(material_id, uid):
    """Cascade delete all rows for a material"""

    def _delete(session, table_name, **where):
        session.delete(table_name, _where(table_name, where))

    def _select_id(session, table_name, **where):
        return [
            v[f"{table_name}_id"]
            for v in session.select(table_name, _where(table_name, where)).all()
        ]

    def _where(table_name, fields):
        rv = PKDict(fields)
        if table_name == "material":
            rv.uid = uid
        return rv

    with _session() as s:
        if len(_select_id(s, "material", material_id=material_id)) < 1:
            # Possible with two simultaneous deletes, but highly unlikely
            # TODO(robnagler) assert?
            pkdlog("unexpected not found material_id={} uid={}", material_id, uid)
            return False
        for p in _select_id(s, "material_property", material_id=material_id):
            for v in _select_id(s, "material_property_value", material_property_id=p):
                _delete(s, "independent_variable_value", material_property_value_id=v)
            _delete(s, "material_property_value", material_property_id=p)
            _delete(s, "independent_variable", material_property_id=p)
        for p in _select_id(s, "plot", material_id=material_id):
            _delete(s, "plot_legend", plot_id=p)
            _delete(s, "plot_point", plot_id=p)
        for t in (
            "material_property",
            "material_component",
            "plot",
            "sim_summary_value",
            "sim_summary",
            "material",
        ):
            _delete(s, t, material_id=material_id)
    return True


def featured_materials():
    with _session() as s:
        return [
            _row_values(r, ("material_id", "material_name", "is_plasma_facing"))
            for r in s.select(
                "material", where=PKDict(is_featured=True, is_public=True)
            ).all()
        ]


def init_module(**imports):
    global _meta

    u = pykern.sql_db.sqlite_uri(_path())
    if _meta is not None and _meta.uri == u:
        return
    sirepo.util.setattr_imports(imports)

    def _optional(v):
        return f"{v} nullable"

    f = "float 64"
    _meta = pykern.sql_db.Meta(
        uri=u,
        schema=PKDict(
            material=PKDict(
                material_id="primary_id 1",
                uid="str 8 index",
                created="datetime index",
                material_name="str 100",
                availability_factor=_optional(f),
                density_g_cm3=f,
                is_atom_pct="bool",
                is_bare_tile=_optional("bool"),
                is_featured=_optional("bool"),
                is_homogenized_divertor=_optional("bool"),
                is_homogenized_hcpb=_optional("bool"),
                is_homogenized_wcll=_optional("bool"),
                is_neutron_source_dt=_optional("bool"),
                is_plasma_facing="bool",
                is_public=_optional("bool"),
                neutron_wall_loading=_optional("str 32"),
                structure=_optional("str 100"),
                microstructure=_optional("str 500"),
                processing_steps=_optional("str 500"),
                unique=(("uid", "material_name"),),
            ),
            material_component=PKDict(
                material_component_id="primary_id 2",
                material_id="primary_id",
                material_component_name="str 8",
                max_pct=_optional(f),
                min_pct=_optional(f),
                target_pct=f,
                unique=(("material_id", "material_component_name"),),
            ),
            material_property=PKDict(
                material_property_id="primary_id 3",
                material_id="primary_id",
                property_name="str 100",
                property_unit="str 32",
                doi_or_url=_optional("str 500"),
                source=_optional("str 32"),
                pointer=_optional("str 32"),
                comments=_optional("str 5000"),
                unique=(("material_id", "property_name"),),
            ),
            material_property_value=PKDict(
                material_property_value_id="primary_id 4",
                material_property_id="primary_id",
                value=f,
                uncertainty=_optional(f),
                temperature_k=_optional(f),
                neutron_fluence_1_cm2=_optional(f),
            ),
            independent_variable=PKDict(
                independent_variable_id="primary_id 5",
                material_property_id="primary_id",
                name="str 100",
                unique=(("material_property_id", "name"),),
            ),
            independent_variable_value=PKDict(
                independent_variable_id="primary_id primary_key index",
                material_property_value_id="primary_id primary_key index",
                value=f,
            ),
            plot=PKDict(
                plot_id="primary_id 6",
                material_id="primary_id index",
                model="str 100",
                stat="str 100 index",
                title="str 100",
                xlabel="str 100",
                ylabel="str 100",
                plot_type="str 10",
            ),
            plot_point=PKDict(
                plot_id="primary_id primary_key index",
                # plot dimension 0: x, 1: y1, 2: y2 ...
                dim="int 32 primary_key",
                idx="int 32 primary_key",
                point=f,
            ),
            plot_legend=PKDict(
                plot_id="primary_id primary_key index",
                # plot dimension 0: x, 1: y1, 2: y2 ...
                dim="int 32 primary_key",
                label="str 100",
            ),
            sim_summary=PKDict(
                material_id="primary_id primary_key index",
                model="str 100 primary_key",
                completed="datetime",
                version="str 100",
            ),
            sim_summary_value=PKDict(
                material_id="primary_id primary_key index",
                model="str 100 primary_key",
                name="str 100 primary_key",
                value=f,
            ),
        ),
    )


def insert_material(parsed, uid):
    def _insert_property(session, name, values):
        vals = values.pop("vals")
        ivars = values.pop("independent_variables", PKDict())
        prop_id = session.insert(
            "material_property",
            property_name=name,
            **values,
        ).material_property_id
        ivar_ids = {
            name: session.insert(
                "independent_variable",
                material_property_id=prop_id,
                name=name,
            ).independent_variable_id
            for name in ivars
        }
        for idx, val in enumerate(vals):
            val_id = session.insert(
                "material_property_value",
                material_property_id=prop_id,
                **val,
            ).material_property_value_id
            for name, values_list in ivars.items():
                if idx < len(values_list) and values_list[idx] is not None:
                    session.insert(
                        "independent_variable_value",
                        independent_variable_id=ivar_ids[name],
                        material_property_value_id=val_id,
                        value=values_list[idx],
                    )

    def _values(cols, vals):
        return PKDict((c, vals[c]) for c in cols if c in vals)

    with _session() as s:
        try:
            rv = s.insert(
                "material",
                _values(s.t.material.columns.keys(), parsed).pkupdate(uid=uid),
            )
        except sqlalchemy.exc.IntegrityError as e:
            if "unique" in str(e).lower():
                # Needs to raise to signal to the session to rollback
                raise Error(f"material name={parsed.material_name} already exists")
            raise
        for v in parsed.components.values():
            s.insert(
                "material_component",
                _values(s.t.material_component.columns.keys(), v).pkupdate(
                    material_id=rv.material_id
                ),
            )
        for n in parsed.properties:
            if not parsed.properties[n].property_unit:
                parsed.properties[n].property_unit = "1"
            _insert_property(
                s, n, parsed.properties[n].pkupdate(material_id=rv.material_id)
            )
        return PKDict((k, rv[k]) for k in ("material_id", "material_name"))


def list_materials(uid):
    def _sim_summary_values(session, material_id):
        return PKDict(
            [
                (r["name"], r["value"])
                for r in s.select(
                    "sim_summary_value", where=PKDict(material_id=material_id)
                ).all()
            ]
        )

    with _session() as s:
        return [
            _row_values(
                r,
                (
                    "material_id",
                    "created",
                    "material_name",
                    "is_public",
                    "is_plasma_facing",
                ),
            ).pkupdate(
                _sim_summary_values(s, r["material_id"]),
            )
            for r in s.select("material", where=PKDict(uid=uid)).all()
        ]


def load_summary(material_id, is_public, uid):
    def _format_plot(plot):
        return sirepo.template.cortex.plotdef_to_sim_frame(plot)

    def _load_plot(row):
        p = PKDict(row).pkupdate(
            points=[],
            legend=[
                r["label"]
                for r in s.select(
                    "plot_legend", where=PKDict(plot_id=row.plot_id)
                ).all()
            ],
        )
        for point in s.select(
            sqlalchemy.select(s.t.plot_point)
            .where(s.t.plot_point.c.plot_id == p.plot_id)
            .order_by(s.t.plot_point.c.dim, s.t.plot_point.c.idx)
        ).all():
            if point.idx == 0:
                assert point.dim == len(p.points)
                p.points.append([])
            assert point.idx == len(p.points[point.dim])
            p.points[point.dim].append(point.point)
        return _format_plot(p)

    def _load_plots(session):
        return [
            _load_plot(r)
            for r in s.select("plot", where=PKDict(material_id=material_id)).all()
        ]

    def _load_summary(session):
        r = PKDict()
        for summary in s.select(
            sqlalchemy.select(s.t.sim_summary).where(
                s.t.sim_summary.c.material_id == material_id
            )
        ).all():
            r[summary["model"]] = _row_values(
                summary, ("completed", "version")
            ).pkupdate(
                current_version=sirepo.template.cortex.SIM_VERSION[summary["model"]],
            )
        return r

    with _session() as s:
        # ensure authorized to material
        if is_public:
            _public_material_by_id(s, material_id)
        else:
            _material_by_id(s, material_id, uid)
        return PKDict(
            plots=_load_plots(s),
            sim=_load_summary(s),
        )


def material_detail(material_id, is_public, uid):
    def _record(session, table_name, row):
        return PKDict(
            zip(
                [c.name for c in session.meta.tables[table_name].columns],
                row,
            )
        )

    def _records(session, table_name, record, field):
        return [
            _record(s, table_name, r)
            for r in session.select(table_name, where={field: record[field]}).all()
        ]

    with _session() as s:
        rv = _record(
            s,
            "material",
            (
                _public_material_by_id(s, material_id)
                if is_public
                else _material_by_id(s, material_id, uid)
            ),
        )
        # Makes testing hard, and don't need to return
        rv.pkdel("uid")
        rv.components = _records(s, "material_component", rv, "material_id")
        rv.properties = _records(s, "material_property", rv, "material_id")
        for p in rv.properties:
            p.vals = _records(s, "material_property_value", p, "material_property_id")
            ivs = PKDict(
                [
                    (r.independent_variable_id, r.name)
                    for r in _records(
                        s, "independent_variable", p, "material_property_id"
                    )
                ]
            )
            for mpv in p.vals:
                for iv in _records(
                    s, "independent_variable_value", mpv, "material_property_value_id"
                ):
                    mpv[ivs[iv.independent_variable_id]] = iv.value
        return rv


def public_materials():
    with _session() as s:
        return [
            _row_values(r, ("material_id", "material_name", "is_plasma_facing"))
            for r in s.select("material", where=PKDict(is_public=True)).all()
        ]


def set_featured(material_id, is_featured, uid):
    _update_material(material_id, uid, PKDict(is_featured=is_featured))


def set_public(material_id, is_public, uid):
    _update_material(material_id, uid, PKDict(is_public=is_public))


def update_sim_summary(summary, uid):
    with _session() as s:
        # ensure authorized to material
        _material_by_id(s, summary.material_id, uid)

        s.delete(
            "sim_summary_value",
            PKDict(material_id=summary.material_id, model=summary.model),
        )
        s.delete(
            "sim_summary",
            PKDict(material_id=summary.material_id, model=summary.model),
        )
        s.insert(
            "sim_summary",
            PKDict(
                {
                    n: summary[n]
                    for n in ("material_id", "model", "completed", "version")
                }
            ),
        )
        for k, v in summary["values"].items():
            s.insert(
                "sim_summary_value",
                PKDict({n: summary[n] for n in ("material_id", "model")}).pkupdate(
                    name=k,
                    value=v,
                ),
            )

        for p in summary.plots:
            _insert_plot(s, p, uid)


def _insert_plot(session, plotdef, uid):
    def _insert():
        return session.insert(
            "plot",
            PKDict(
                {
                    k: plotdef[k]
                    for k in (
                        "material_id",
                        "title",
                        "model",
                        "stat",
                        "xlabel",
                        "ylabel",
                        "plot_type",
                    )
                }
            ),
        ).plot_id

    def _insert_plot_legend(plot_id):
        for dim, label in enumerate(plotdef.legend):
            session.insert(
                "plot_legend",
                PKDict(
                    plot_id=plot_id,
                    dim=dim,
                    label=label,
                ),
            )

    def _insert_plot_points(plot_id):
        for dim, points in enumerate(plotdef["points"]):
            for idx, v in enumerate(points):
                session.insert(
                    "plot_point",
                    PKDict(
                        plot_id=plot_id,
                        dim=dim,
                        idx=idx,
                        point=v,
                    ),
                )

    if m := session.select_one_or_none(
        "plot",
        where=PKDict(
            material_id=plotdef.material_id, model=plotdef.model, stat=plotdef.stat
        ),
    ):
        for n in ("plot_legend", "plot_point", "plot"):
            session.delete(n, PKDict(plot_id=m.plot_id))
    p = _insert()
    _insert_plot_legend(p)
    _insert_plot_points(p)


def _material_by_id(session, material_id, uid):
    return session.select_one(
        "material", where=PKDict(material_id=material_id, uid=uid)
    )


def _public_material_by_id(session, material_id):
    return session.select_one(
        "material", where=PKDict(material_id=material_id, is_public=True)
    )


def _path():
    return sirepo.srdb.root().join(_BASE)


def _row_values(row, names):
    def _convert(row, name):
        if name in ("created", "completed"):
            return int(row[name].timestamp())
        return row[name]

    return PKDict([(n, _convert(row, n)) for n in names])


def _session():
    return _meta.session()


def _update_material(material_id, uid, values):
    with _session() as s:
        # ensure authorized to material
        s.execute(
            sqlalchemy.update(s.t.material)
            .values(values)
            .where(s.t.material.c.material_id == material_id)
        )
