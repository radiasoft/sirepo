# -*- coding: utf-8 -*-
"""CLI for CloudMC

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from pymoab.rng import Range
from sirepo import mpi
from sirepo.template import template_common
import array
import copy
import json
import multiprocessing
import py.path
import pymoab.core
import pymoab.types
import re
import sirepo.simulation_db
import sirepo.template.cloudmc
import sirepo.util
import uuid


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


def extract_dagmc(dagmc_filename):
    mb = pymoab.core.Core()
    mb.load_file(dagmc_filename)
    visited = set()
    res = PKDict()
    work_items = []
    for name, volumes in _groups_and_volumes(mb).items():
        if _visited_volume(volumes, visited):
            continue
        vol_id = _get_tag_value(
            mb,
            mb.tag_get_handle(pymoab.types.GLOBAL_ID_TAG_NAME),
            volumes[0],
        )
        res[name] = PKDict(
            name=name,
            volId=vol_id,
        )
        work_items.append((dagmc_filename, vol_id, volumes))
    work_items.sort(key=lambda v: -len(v[2]))
    with multiprocessing.Pool(mpi.cfg().cores) as pool:
        pool.starmap(_extract_group, work_items, 1)
    return res


def run(cfg_dir):
    template_common.exec_parameters()
    data = sirepo.simulation_db.read_json(template_common.INPUT_BASE_NAME)
    sirepo.template.cloudmc.extract_report_data(pkio.py_path(cfg_dir), data)


def _array_from_list(arr, arr_type):
    res = array.array(arr_type)
    res.fromlist(arr)
    return res


def _extract_group(dagmc_filename, vol_id, volumes):
    mb = pymoab.core.Core()
    mb.load_file(dagmc_filename)
    _write_vti(vol_id, _get_points_and_polys(mb, volumes))


def _get_tag_value(mb, tag, handle):
    return str(mb.tag_get_data(tag, handle).flat[0])


def _get_points_and_polys(mb, volumes):
    verticies = Range()
    triangles = Range()
    for h in volumes:
        _get_verticies_and_triangles(mb, h, verticies, triangles)
    m = {}
    for i, v in enumerate(verticies):
        m[v] = i
    polys = []
    for t in triangles:
        polys.append(3)
        polys += [m[vert] for vert in mb.get_connectivity(t)]
    return PKDict(
        points=_array_from_list(list(mb.get_coords(verticies)), "f"),
        polys=_array_from_list(polys, "I"),
    )


def _get_verticies_and_triangles(mb, handle, verticies, triangles, visited=None):
    if visited is None:
        visited = set()
    verticies.merge(mb.get_entities_by_type(handle, pymoab.types.MBVERTEX))
    triangles.merge(mb.get_entities_by_type(handle, pymoab.types.MBTRI))
    for c in mb.get_child_meshsets(handle):
        if c in visited:
            continue
        visited.add(c)
        _get_verticies_and_triangles(mb, c, verticies, triangles, visited)


def _groups_and_volumes(mb):
    res = PKDict()
    name_h = mb.tag_get_handle(pymoab.types.NAME_TAG_NAME)
    for group in mb.get_entities_by_type_and_tag(
        mb.get_root_set(),
        pymoab.types.MBENTITYSET,
        [mb.tag_get_handle(pymoab.types.CATEGORY_TAG_NAME)],
        ["Group"],
    ):
        name = _parse_entity_name(_get_tag_value(mb, name_h, group))
        if not name:
            continue
        v = [h for h in mb.get_entities_by_handle(group)]
        if name in res:
            res[name] = v + res[name]
        else:
            res[name] = v
    return res


def _parse_entity_name(name):
    m = re.search("^mat:(.*)$", name)
    if m:
        return m.group(1)
    return None


def _visited_volume(volumes, visited):
    for h in volumes:
        if h in visited:
            pkdlog(f"skipping volume used in multiple groups: {h} {name}")
            return True
        visited.add(h)
    return False


def _write_vti(vol_id, geometry):
    pkio.unchecked_remove(vol_id)
    pkio.mkdir_parent(f"{vol_id}/{_DATA_DIR}")
    vti = copy.deepcopy(_VTI_TEMPLATE)
    vti.metadata.name = f"{vol_id}.vtp"
    fns = []
    for n in ("polys", "points"):
        if n not in vti:
            continue
        fn = str(uuid.uuid1()).replace("-", "")
        with open(f"{vol_id}/{_DATA_DIR}/{fn}", "wb") as f:
            geometry[n].tofile(f)
        vti[n].ref.id = fn
        vti[n].size = int(len(geometry[n]))
        fns.append(f"{_DATA_DIR}/{fn}")
    with sirepo.util.write_zip(f"{vol_id}.zip") as f:
        f.writestr("index.json", json.dumps(vti))
        for fn in fns:
            f.write(f"{vol_id}/{fn}", arcname=fn)
    pkio.unchecked_remove(vol_id)
