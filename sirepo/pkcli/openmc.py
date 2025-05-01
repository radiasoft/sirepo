# -*- coding: utf-8 -*-
"""CLI for OpenMC

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import copy
import h5py
import json
import numpy
import pymeshlab
import re
import sirepo.const
import sirepo.mpi
import sirepo.simulation_db
import sirepo.util
import subprocess
import uuid

try:
    from dagmc import DAGModel
except:
    from pydagmc import Model as DAGModel


_DECIMATION_MAX_POLYGONS = 10000


def create_standard_materials_file(compendium_filename):
    import sirepo.template.openmc

    m = pkjson.load_any(pkio.read_text(compendium_filename))
    dt = numpy.dtype([("name", h5py.string_dtype()), ("ao", "f4")])
    with h5py.File(sirepo.template.openmc.STANDARD_MATERIALS_DB, mode="w") as f:
        for d in m.data:
            v = PKDict(
                name=d.Name,
                density_g_cc=d.Density,
                elements=[],
                nuclides=[],
            )
            for e in d.Elements:
                v.elements.append((e.Element, e.AtomFraction_whole))
                for i in e.Isotopes:
                    v.nuclides.append((i.Isotope, i.AtomFraction_whole))

            g = f.create_group(f"/{d.Name}")
            g.attrs["density_g_cc"] = v.density_g_cc
            g.create_dataset("elements", data=numpy.array(v.elements, dtype=dt))
            g.create_dataset("nuclides", data=numpy.array(v.nuclides, dtype=dt))


def extract_dagmc(dagmc_filename):
    s = pkio.py_path(sirepo.const.SIM_RUN_INPUT_BASENAME)
    dm = None
    if s.exists():
        dm = sirepo.simulation_db.read_json(s).models
    gc = _MoabGroupCollector(dagmc_filename, dm)
    sirepo.mpi.restrict_ops_to_first_node(_MoabGroupExtractor(gc).get_items())
    res = PKDict()
    for g in gc.groups:
        res[g.name] = PKDict(
            name=g.name,
            volId=g.vol_id,
            density=g.density,
        )
    return res


def geometry_xml_to_h5m(geometry_xml_filename, output_dagmc_filename, threads=1):
    import geouned

    s = "out"
    geouned.CsgToCad().export_cad(
        csg_format="openmc_xml",
        input_filename=geometry_xml_filename,
        output_filename=s,
    )
    step_to_dagmc(f"{s}.step", output_dagmc_filename, threads, scale=1.0)


def step_to_dagmc(input_step_filename, output_dagmc_filename, threads=1, scale=0.1):
    """Convert a CAD step (.stp or .step) file to dagmc (.h5m) file.

    A sanity check (check_watertight) is performed on the output file.

    Args:
      input_step_filename (str): STEP input file
      output_dagmc_filename (str): DAGMC output file
      threads (int): number of thread used for conversion (optional)
    """
    import CAD_to_OpenMC.assembly

    if not re.search(r"\.ste?p", input_step_filename, re.IGNORECASE) or not re.search(
        r"\.h5m", output_dagmc_filename, re.IGNORECASE
    ):
        raise AssertionError(
            f"input_step_filename={input_step_filename} must be .stp and output_dagmc_filename={output_dagmc_filename} must be .h5m"
        )
    CAD_to_OpenMC.assembly.mesher_config["threads"] = threads
    CAD_to_OpenMC.assembly.mesher_config["mesh_algorithm"] = 2
    a = CAD_to_OpenMC.assembly.Assembly([input_step_filename])
    a.set_tag_delim(r".*")
    a.import_stp_files(scale=scale)
    a.merge_all()
    a.solids_to_h5m(backend="gmsh", h5m_filename=output_dagmc_filename)
    o = subprocess.check_output(("check_watertight", output_dagmc_filename))
    r = re.findall(rb"(\(0%\) unsealed)", o)
    if len(r) != 2:
        d = pkcompat.from_bytes(o).replace("\n", " ")
        raise AssertionError(
            f"stp file could not be converted to watertight dagmc: {d}"
        )


class _MoabGroupCollector:
    def __init__(self, dagmc_filename, sim_models):
        self.dagmc_filename = dagmc_filename
        self.groups = self._groups_and_volumes(sim_models)

    def _groups_and_volumes(self, sim_models):
        res = PKDict()
        for g in DAGModel(self.dagmc_filename).groups_by_name.values():
            n, d = self._parse_entity_name_and_density(g.name)
            if not n:
                continue
            if not g.name.startswith("mat:"):
                continue
            v = g.volumes
            if not v:
                continue
            res[n] = PKDict(
                name=n,
                full_name=g.name,
                density=d,
                volume_count=len(v),
                vol_id=self._volume_id(n, v, sim_models),
            )
        for g in res.values():
            if re.search(r"\_comp$", g.name):
                g.name = re.sub(r"\_comp$", "", g.name)
                g.is_complement = True
        return tuple(res.values())

    def _parse_entity_name_and_density(self, name):
        m = re.search(r"^mat:(.*?)(?:/rho:(.*))?$", name)
        if m:
            return m.group(1), m.group(2)
        return None, None

    def _volume_id(self, name, volumes, sim_models):
        # for backward compatibility, allows finding a volume from an
        # old import which assigned volId differently
        if sim_models and "volumes" in sim_models and name in sim_models.volumes:
            return sim_models.volumes[name].volId
        return str(volumes[0].id)


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
                    full_name=g.full_name,
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
        t, v = (
            DAGModel(item.dagmc_filename)
            .groups_by_name[item.full_name]
            .get_triangle_conn_and_coords(True)
        )
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
