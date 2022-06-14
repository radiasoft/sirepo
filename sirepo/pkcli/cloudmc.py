# -*- coding: utf-8 -*-
"""CLI for CloudMC

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import array
import copy
import io
import json
import os
import re
import sirepo.sim_data.cloudmc
import sirepo.simulation_db
import sirepo.template.cloudmc
import subprocess
import uuid
import zipfile


_DATA_DIR = 'data'
_VTI_TEMPLATE = PKDict(
    CellData=PKDict(),
    FieldData=PKDict(),
    vtkClass='vtkPolyData',
    lines=PKDict(
        name='_lines',
        numberOfComponents=1,
        dataType='Uint32Array',
        vtkClass='vtkCellArray',
        ref=PKDict(
            encode='LittleEndian',
            basepath=_DATA_DIR,
            id=None,
        ),
        size=None,
    ),
    polys=PKDict(
        name='_polys',
        numberOfComponents=1,
        dataType='Uint32Array',
        vtkClass='vtkCellArray',
        ref=PKDict(
            encode='LittleEndian',
            basepath=_DATA_DIR,
            id=None,
        ),
        size=None,
    ),
    PointData=PKDict(),
    points=PKDict(
        name='Points',
        numberOfComponents=3,
        dataType='Float32Array',
        vtkClass='vtkPoints',
        ref=PKDict(
            encode='LittleEndian',
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
    if 'report' in data and data.report == 'dagmcAnimation':
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
    n = f'{name}s'
    if res[n] is None:
        raise AssertionError(f'Missing {n}')
    c = res[f'{name}_count']
    if len(res[n]) != c:
        raise AssertionError(f'{n} do not match count: {len(res[n])} != {c}')


def _extract_volumes(filename):
    res = PKDict()
    entities = _parse_volumes(filename)
    visited = PKDict()
    for e in entities.values():
        if e.CATEGORY == 'Group':
            name = _parse_entity_name(e.NAME)
            if not name:
                continue
            vol_ids = []
            for i in e.volumes:
                vol_ids.append(entities[i].GLOBAL_ID)
            res[name] = PKDict(
                volId=vol_ids[0],
            )
            for i in vol_ids:
                if i in visited:
                    raise AssertionError(f'volume used in multiple groups: {i} {e}')
                visited[i] = True
            os.system(f'mbconvert -v {",".join(vol_ids)} {filename} {vol_ids[0]}.vtk')
    return res


def _parse_attr(name, line, entity=None):
    m = re.search(f'^\s*{name} =?\s*(.*?)$', line)
    if m:
        v = m.group(1)
        if entity is not None:
            entity[name] = v.strip()
        return True
    return False


def _parse_entity_name(name):
    m = re.search('^mat:(.*)$', name)
    if m:
        return m.group(1)
    return None

def _parse_entity_set(entity_set):
    m = re.search('^(\d+) \- (\d+)$', entity_set)
    if m:
        return [str(x) for x in range(int(m.group(1)), int(m.group(2)) + 1)]
    assert re.search('^(\d+)$', entity_set)
    return [entity_set]


def _parse_volumes(filename):
    res = PKDict()
    e = None
    # using subprocess not pksubprocess because we don't want to read in all
    # the output at once which can be hundreds of megabytes
    p = subprocess.Popen(['mbsize', '-ll', filename], stdout=subprocess.PIPE)
    for line in io.TextIOWrapper(p.stdout, encoding='ascii'):
        if e and re.search('^\s*$', line):
            if 'CATEGORY' in e:
                res[e.MBENTITYSET] = e
            e = None
            continue
        if _parse_attr('MBENTITYSET', line):
            assert e is None
            e = PKDict(volumes=[])
            assert _parse_attr('MBENTITYSET', line, e)
            continue
        if not e:
            continue
        if _parse_attr('GLOBAL_ID', line, e):
            continue
        if _parse_attr('EntitySet', line, e):
            e.volumes += _parse_entity_set(e.EntitySet)
            continue
        if _parse_attr('CATEGORY', line, e):
            if e.CATEGORY not in ('Volume', 'Group'):
                e = None
            continue
        if _parse_attr('NAME', line, e):
            continue
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
    state = 'header'
    with pkio.open_text(str(filename)) as f:
        for line in f:
            if state == 'header':
                m = re.match(r'^POINTS (\d+)', line)
                if m:
                    res.point_count = int(m.group(1)) * 3
                    state = 'points'
            elif state == 'points':
                m = re.match(r'^CELLS \d+ (\d+)', line)
                if m:
                    res.cell_count = int(m.group(1))
                    state = 'cells'
                    continue
                p = [float(v) for v in line.split(' ')]
                if len(p) != 3:
                    raise AssertionError(f'Invalid point: {p}')
                res.points += p
            elif state == 'cells':
                m = re.match(r'^CELL_TYPES', line)
                if m:
                    break
                p = [int(v) for v in line.split(' ')]
                if p[0] == 2:
                    res.lines += p
                    res.line_count += len(p)
                else:
                    res.polys += p
                    res.poly_count += len(p)
    _assert_size(res, 'point')
    _assert_size(res, 'line')
    _assert_size(res, 'poly')
    if res.line_count + res.poly_count != res.cell_count:
        raise AssertionError('line and poly count != cell count')
    return PKDict(
        points=_array_from_list(res.points, 'f'),
        lines=_array_from_list(res.lines, 'I'),
        polys=_array_from_list(res.polys, 'I'),
    )


def _vtk_to_bin(vol_id):
    filename = f'{vol_id}.vtk'
    v = _parse_vtk(filename)
    pkio.unchecked_remove(_DATA_DIR)
    pkio.mkdir_parent(_DATA_DIR)
    vti = copy.deepcopy(_VTI_TEMPLATE)
    vti.metadata.name = f'{vol_id}.vtp'
    if not len(v.lines):
        del vti['lines']
    fns = []
    for n in ('lines', 'polys', 'points'):
        if n not in vti:
            continue
        fn = str(uuid.uuid1()).replace('-', '')
        with open (f'{_DATA_DIR}/{fn}', 'wb') as f:
            v[n].tofile(f)
        vti[n].ref.id = fn
        vti[n].size = int(len(v[n]))
        fns.append(f'{_DATA_DIR}/{fn}')
    with zipfile.ZipFile(f'{vol_id}.zip', 'w') as f:
        f.writestr('index.json', json.dumps(vti))
        for fn in fns:
            f.write(fn)
    pkio.unchecked_remove(_DATA_DIR)
    pkio.unchecked_remove(filename)


#TODO(pjm): when pymoab is available, replace the mbsize parsing with something like this

# from pykern.pkcollections import PKDict
# from pymoab import core, types
# import re
# import sys

# def get_volumes_by_group(filename):

#     def get_tag_value(mb, tag, handle):
#         return mb.tag_get_data(tag, handle).flat[0]

#     mb = core.Core()
#     mb.load_file(filename)
#     name_h = mb.tag_get_handle(types.NAME_TAG_NAME)
#     id_h = mb.tag_get_handle(types.GLOBAL_ID_TAG_NAME)
#     res = PKDict()
#     for group in mb.get_entities_by_type_and_tag(
#         mb.get_root_set(),
#         types.MBENTITYSET,
#         [mb.tag_get_handle(types.CATEGORY_TAG_NAME)],
#         ['Group'],
#     ):
#         name = get_tag_value(mb, name_h, group)
#         if not re.search(r'^mat:', name):
#             continue
#         assert not res.get(group)
#         res[group] = PKDict(
#             name=name,
#             volumes=[],
#         )
#         for volume in mb.get_entities_by_handle(group):
#             res[group].volumes.append(get_tag_value(mb, id_h, volume))
#     return res

# assert len(sys.argv) == 2, f'usage: python {sys.argv[0]} <filename>'
# res = get_volumes_by_group(sys.argv[1])
# print(res)
