# -*- coding: utf-8 -*-
"""CLI for OpenMC

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import copy
import json
import numpy
import pymeshlab
import pymoab.core
import pymoab.rng
import pymoab.types
import re
import sirepo.mpi
import sirepo.simulation_db
import sirepo.util
import subprocess
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
            density=g.density,
        )
    return res


def step_to_dagmc(input_step_filename, output_dagmc_filename, threads=1):
    """Convert a CAD step (.stp) file to dagmc (.h5m) file.

    A sanity check (check_watertight) is performed on the output file.

    Args:
      input_step_filename (str): .stp input file
      output_dagmc_filename (str): .h5m output file
      threads (int): number of thread used for conversion (optional)
    """
    import CAD_to_OpenMC.assembly

    if not input_step_filename.endswith(".stp") or not output_dagmc_filename.endswith(
        ".h5m"
    ):
        raise AssertionError(
            f"input_step_filename={input_step_filename} must be .stp and output_dagmc_filename={output_dagmc_filename} must be .h5m"
        )
    CAD_to_OpenMC.assembly.mesher_config["threads"] = threads
    a = CAD_to_OpenMC.assembly.Assembly([input_step_filename])
    a.import_stp_files()
    a.merge_all()
    a.solids_to_h5m(backend="stl", h5m_filename=output_dagmc_filename)
    o = subprocess.check_output(("check_watertight", output_dagmc_filename))
    r = re.findall(rb"(\(0%\) unsealed)", o)
    if len(r) != 2:
        d = pkcompat.from_bytes(o).replace("\n", " ")
        raise AssertionError(
            f"stp file could not be converted to watertight dagmc: {d}"
        )


class _MoabGroupCollector:
    def __init__(self, dagmc_filename):
        mb = pymoab.core.Core()
        mb.load_file(dagmc_filename)
        self.dagmc_filename = dagmc_filename
        self._id_tag = self._tag(mb, "GLOBAL_ID")
        self._name_tag = self._tag(mb, "NAME")
        self.groups = self._groups_and_volumes(mb)

    def _groups(self, mb):
        for g in mb.get_entities_by_type_and_tag(
            mb.get_root_set(),
            pymoab.types.MBENTITYSET,
            [self._tag(mb, "CATEGORY")],
            ["Group"],
        ):
            yield g

    def _groups_and_volumes(self, mb):
        res = PKDict()
        for g in self._groups(mb):
            n, d = self._parse_entity_name_and_density(mb, g)
            if not n:
                continue
            v = [h for h in mb.get_entities_by_handle(g)]
            if not v:
                continue
            res.pksetdefault(n, lambda: PKDict(name=n, volumes=[], density=d))
            res[n].volumes[0:0] = v
        for g in res.values():
            g.vol_id = self._tag_value(mb, self._id_tag, g.volumes[0])
            if re.search(r"\_comp$", g.name):
                g.name = re.sub(r"\_comp$", "", g.name)
                g.is_complement = True
        return tuple(res.values())

    def _parse_entity_name_and_density(self, mb, group):
        m = re.search(
            r"^mat:(.*?)(?:/rho:(.*))?$", self._tag_value(mb, self._name_tag, group)
        )
        if m:
            return m.group(1), m.group(2)
        return None, None

    def _tag(self, mb, name):
        return mb.tag_get_handle(getattr(pymoab.types, f"{name}_TAG_NAME"))

    def _tag_value(self, mb, tag, handle):
        return str(mb.tag_get_data(tag, handle).flat[0])


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
                    name=g.name,
                    vol_id=g.vol_id,
                    volumes=g.volumes,
                    processor=self,
                )
            )
        # process longest volume sets first
        self._items.sort(key=lambda v: -len(v.volumes))

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
        def _reshape3(v):
            return v.reshape(int(len(v) / 3), 3)

        mb = pymoab.core.Core()
        mb.load_file(item.dagmc_filename)
        vr = pymoab.rng.Range()
        tr = pymoab.rng.Range()
        for h in item.volumes:
            self._get_verticies_and_triangles(mb, h, vr, tr)
        return (
            _reshape3(mb.get_coords(vr)),
            _reshape3(numpy.searchsorted(vr, mb.get_connectivity(tr))),
        )

    def _get_points_and_polys(self, points, polys):
        return PKDict(
            points=points.ravel(),
            # inserts polygon point count (always 3 for triangles)
            polys=numpy.insert(polys, 0, 3, axis=1).ravel(),
        )

    def _get_verticies_and_triangles(
        self, mb, handle, verticies, triangles, visited=None
    ):
        if visited is None:
            visited = set()
        verticies.merge(mb.get_entities_by_type(handle, pymoab.types.MBVERTEX))
        triangles.merge(mb.get_entities_by_type(handle, pymoab.types.MBTRI))
        for c in mb.get_child_meshsets(handle):
            if c in visited:
                continue
            visited.add(c)
            self._get_verticies_and_triangles(mb, c, verticies, triangles, visited)

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
