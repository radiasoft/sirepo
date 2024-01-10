# -*- coding: utf-8 -*-
"""CLI for CloudMC

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import copy
import dagmc.dagnav
import json
import numpy
import pymeshlab
import re
import sirepo.mpi
import sirepo.simulation_db
import sirepo.util
import uuid

_DECIMATION_MAX_POLYGONS = 10000


def extract_dagmc(dagmc_filename):
    gc = _MoabGroupCollector(dagmc_filename)
    sirepo.mpi.restrict_ops_to_first_node(_MoabGroupExtractor(gc).get_items())
    res = PKDict()
    for g in gc.groups:
        res[g.name] = PKDict(
            name=g.name,
            volId=g.vol_id,
        )
    return res


def run(cfg_dir):
    template_common.exec_parameters()
    data = sirepo.simulation_db.read_json(template_common.INPUT_BASE_NAME)
    sirepo.template.import_module("cloudmc").extract_report_data(
        pkio.py_path(cfg_dir), data
    )


class _MoabGroupCollector:
    def __init__(self, dagmc_filename):
        self.dagmc_filename = dagmc_filename
        self.groups = self._groups_and_volumes()

    def _groups_and_volumes(self):
        res = PKDict()
        for g in dagmc.dagnav.groups_from_file(self.dagmc_filename).values():
            if not g.name.startswith("mat:"):
                continue
            v = g.get_volumes()
            if not v:
                continue
            res[g.name] = PKDict(
                name=g.name,
                volume_count=len(v),
                # for historical reasons the vol_id for the group is the last volume's id
                vol_id=str(list(v)[-1]),
            )
        for g in res.values():
            if re.search(r"\_comp$", g.name):
                g.name = re.sub(r"\_comp$", "", g.name)
                g.is_complement = True
        return tuple(res.values())


class _MoabGroupExtractor:
    _DATA_DIR = "data"
    _VTI_TEMPLATE = PKDict(
        CellData=PKDict(),
        FieldData=PKDict(),
        vtkClass="vtkPolyData",
        polys=PKDict(
            name="_polys",
            numberOfComponents=1,
            dataType="Uint32Array",
            vtkClass="vtkCellArray",
            ref=PKDict(
                encode="LittleEndian",
                basepath=_DATA_DIR,
                id=None,
            ),
            size=None,
        ),
        PointData=PKDict(),
        points=PKDict(
            name="Points",
            numberOfComponents=3,
            dataType="Float32Array",
            vtkClass="vtkPoints",
            ref=PKDict(
                encode="LittleEndian",
                basepath=_DATA_DIR,
                id=None,
            ),
            size=None,
        ),
        metadata=PKDict(
            name=None,
        ),
    )

    def __init__(self, collector):
        self._items = []
        for g in collector.groups:
            if g.get("is_complement"):
                continue
            self._items.append(
                _MoabGroupExtractorOp(
                    dagmc_filename=collector.dagmc_filename,
                    vol_id=g.vol_id,
                    volume_count=g.volume_count,
                    name=g.name,
                    processor=self,
                )
            )
        # process longest volume sets first
        self._items.sort(key=lambda v: -v.volume_count)

    def get_items(self):
        return self._items

    def process_item(self, item):
        v, p = self._decimate(*self._extract_moab_vertices_and_triangles(item))
        self._write_vti(item.vol_id, self._get_points_and_polys(v, p))
        self._write_mesh(item.vol_id, v, p)

    def _decimate(self, vertices, polygons):
        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(vertices, polygons))
        c = len(ms.current_mesh().face_matrix())
        if c > _DECIMATION_MAX_POLYGONS:
            ms.apply_filter(
                "meshing_decimation_quadric_edge_collapse",
                preservenormal=True,
                targetperc=max(0.2, _DECIMATION_MAX_POLYGONS / c),
            )
        m = ms.current_mesh()
        pkdlog(
            "reduce faces: {} to {} ({}%)",
            c,
            len(m.face_matrix()),
            int(100 - len(m.face_matrix()) * 100 / c),
        )
        return (
            m.vertex_matrix().astype(numpy.float32),
            m.face_matrix().astype(numpy.uint32),
        )

    def _extract_moab_vertices_and_triangles(self, item):
        t, v = dagmc.dagnav.groups_from_file(item.dagmc_filename)[
            item.name
        ].get_triangle_conn_and_coords(True)
        return (v, t)

    def _get_points_and_polys(self, points, polys):
        return PKDict(
            points=points.ravel(),
            # inserts polygon point count (always 3 for triangles)
            polys=numpy.insert(polys, 0, 3, axis=1).ravel(),
        )

    def _write_mesh(self, vol_id, points, polys):
        ms = pymeshlab.MeshSet()
        ms.add_mesh(pymeshlab.Mesh(points, polys))
        ms.save_current_mesh(f"{vol_id}.ply")

    def _write_vti(self, vol_id, geometry):
        pkio.unchecked_remove(vol_id)
        p = pkio.mkdir_parent(f"{vol_id}/{_MoabGroupExtractor._DATA_DIR}")
        vti = copy.deepcopy(_MoabGroupExtractor._VTI_TEMPLATE)
        vti.metadata.name = f"{vol_id}.vtp"
        fns = []
        for n in ("polys", "points"):
            fn = str(uuid.uuid1()).replace("-", "")
            with open(str(p.join(fn)), "wb") as f:
                geometry[n].tofile(f)
            vti[n].ref.id = fn
            vti[n].size = int(len(geometry[n]))
            fns.append(f"{_MoabGroupExtractor._DATA_DIR}/{fn}")
        with sirepo.util.write_zip(f"{vol_id}.zip") as f:
            f.writestr("index.json", json.dumps(vti))
            for fn in fns:
                f.write(f"{vol_id}/{fn}", arcname=fn)
        pkio.unchecked_remove(vol_id)


class _MoabGroupExtractorOp(PKDict):
    def __call__(self):
        self.processor.process_item(self)
