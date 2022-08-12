# -*- coding: utf-8 -*-
"""CLI for CloudMC

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import array
import copy
import json
import os
import pymoab.core
import pymoab.types
import re
import sirepo.sim_data.cloudmc
import sirepo.simulation_db
import sirepo.template.cloudmc
import uuid
import zipfile


_DATA_DIR = "data"
_VTI_TEMPLATE = PKDict(
    CellData=PKDict(),
    FieldData=PKDict(),
    vtkClass="vtkPolyData",
    lines=PKDict(
        name="_lines",
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
    mat = _extract_volumes(dagmc_filename)
    for vol in mat.values():
        _vtk_to_bin(vol.volId)
    return mat


def run_background(cfg_dir):
    data = sirepo.simulation_db.read_json(
        template_common.INPUT_BASE_NAME,
    )
    if "report" in data and data.report == "dagmcAnimation":
        sirepo.simulation_db.write_json(
            sirepo.template.cloudmc.VOLUME_INFO_FILE,
            extract_dagmc(sirepo.sim_data.cloudmc.SimData.dagmc_filename(data)),
        )
        return
    template_common.exec_parameters()


def _array_from_list(arr, arr_type):
    res = array.array(arr_type)
    res.fromlist(arr)
    return res


def _assert_size(res, name):
    n = f"{name}s"
    if res[n] is None:
        raise AssertionError(f"Missing {n}")
    c = res[f"{name}_count"]
    if len(res[n]) != c:
        raise AssertionError(f"{n} do not match count: {len(res[n])} != {c}")


def _extract_volumes(filename):
    res = PKDict()
    visited = PKDict()
    for v in _parse_volumes(filename).values():
        name = _parse_entity_name(v.name)
        if not name:
            continue
        skip_volume = False
        for i in v.volumes:
            if i in visited:
                pkdlog(f"skipping volume used in multiple groups: {i} {name}")
                skip_volume = True
            visited[i] = True
        if skip_volume:
            continue
        res[name] = PKDict(
            volId=v.volumes[0],
        )
        os.system(f'mbconvert -v {",".join(v.volumes)} {filename} {v.volumes[0]}.vtk')
    return res


def _parse_entity_name(name):
    m = re.search("^mat:(.*)$", name)
    if m:
        return m.group(1)
    return None


def _parse_volumes(filename):
    def get_tag_value(mb, tag, handle):
        return str(mb.tag_get_data(tag, handle).flat[0])

    mb = pymoab.core.Core()
    mb.load_file(filename)
    name_h = mb.tag_get_handle(pymoab.types.NAME_TAG_NAME)
    id_h = mb.tag_get_handle(pymoab.types.GLOBAL_ID_TAG_NAME)
    res = PKDict()
    for group in mb.get_entities_by_type_and_tag(
        mb.get_root_set(),
        pymoab.types.MBENTITYSET,
        [mb.tag_get_handle(pymoab.types.CATEGORY_TAG_NAME)],
        ["Group"],
    ):
        name = get_tag_value(mb, name_h, group)
        if not re.search(r"^mat:", name):
            continue
        assert not res.get(group)
        res[group] = PKDict(
            name=name,
            volumes=[],
        )
        for volume in mb.get_entities_by_handle(group):
            res[group].volumes.append(get_tag_value(mb, id_h, volume))
    return res


def _parse_vtk(filename):
    res = PKDict(
        points=[],
        point_count=None,
        lines=[],
        line_count=0,
        polys=[],
        poly_count=0,
        cell_count=None,
    )
    state = "header"
    with pkio.open_text(str(filename)) as f:
        for line in f:
            if state == "header":
                m = re.match(r"^POINTS (\d+)", line)
                if m:
                    res.point_count = int(m.group(1)) * 3
                    state = "points"
            elif state == "points":
                m = re.match(r"^CELLS \d+ (\d+)", line)
                if m:
                    res.cell_count = int(m.group(1))
                    state = "cells"
                    continue
                p = [float(v) for v in line.split(" ")]
                if len(p) != 3:
                    raise AssertionError(f"Invalid point: {p}")
                res.points += p
            elif state == "cells":
                m = re.match(r"^CELL_TYPES", line)
                if m:
                    break
                p = [int(v) for v in line.split(" ")]
                if p[0] == 2:
                    res.lines += p
                    res.line_count += len(p)
                else:
                    res.polys += p
                    res.poly_count += len(p)
    _assert_size(res, "point")
    _assert_size(res, "line")
    _assert_size(res, "poly")
    if res.line_count + res.poly_count != res.cell_count:
        raise AssertionError("line and poly count != cell count")
    return PKDict(
        points=_array_from_list(res.points, "f"),
        lines=_array_from_list(res.lines, "I"),
        polys=_array_from_list(res.polys, "I"),
    )


def _vtk_to_bin(vol_id):
    filename = f"{vol_id}.vtk"
    v = _parse_vtk(filename)
    pkio.unchecked_remove(_DATA_DIR)
    pkio.mkdir_parent(_DATA_DIR)
    vti = copy.deepcopy(_VTI_TEMPLATE)
    vti.metadata.name = f"{vol_id}.vtp"
    if not len(v.lines):
        del vti["lines"]
    fns = []
    for n in ("lines", "polys", "points"):
        if n not in vti:
            continue
        fn = str(uuid.uuid1()).replace("-", "")
        with open(f"{_DATA_DIR}/{fn}", "wb") as f:
            v[n].tofile(f)
        vti[n].ref.id = fn
        vti[n].size = int(len(v[n]))
        fns.append(f"{_DATA_DIR}/{fn}")
    with zipfile.ZipFile(f"{vol_id}.zip", "w") as f:
        f.writestr("index.json", json.dumps(vti))
        for fn in fns:
            f.write(fn)
    pkio.unchecked_remove(_DATA_DIR)
    pkio.unchecked_remove(filename)
