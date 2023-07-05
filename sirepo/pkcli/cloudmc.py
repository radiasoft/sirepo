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
import py.path
import pymoab.core
import pymoab.rng
import pymoab.types
import re
import sirepo.mpi
import sirepo.simulation_db
import sirepo.template.cloudmc
import sirepo.util
import uuid


class MoabGroupCollector:
    def __init__(self, dagmc_filename):
        mb = pymoab.core.Core()
        mb.load_file(dagmc_filename)
        self.dagmc_filename = dagmc_filename
        self.__visited = set()
        self.__id_tag = self.__tag(mb, "GLOBAL_ID")
        self.__name_tag = self.__tag(mb, "NAME")
        self.groups = self.__groups_and_volumes(mb)

    def __groups(self, mb):
        for g in mb.get_entities_by_type_and_tag(
            mb.get_root_set(),
            pymoab.types.MBENTITYSET,
            [self.__tag(mb, "CATEGORY")],
            ["Group"],
        ):
            yield g

    def __groups_and_volumes(self, mb):
        res = PKDict()
        for g in self.__groups(mb):
            name = self.__parse_entity_name(mb, g)
            if name:
                v = self.__volumes(mb, name, g)
                if v:
                    if name in res:
                        v += res[name].volumes
                    else:
                        res[name] = PKDict(
                            name=name,
                        )
                    res[name].volumes = v
        for g in res.values():
            g.vol_id = self.__tag_value(mb, self.__id_tag, g.volumes[0])
        return res.values()

    def __parse_entity_name(self, mb, group):
        m = re.search("^mat:(.*)$", self.__tag_value(mb, self.__name_tag, group))
        if m:
            return m.group(1)
        return None

    def __tag(self, mb, name):
        return mb.tag_get_handle(getattr(pymoab.types, f"{name}_TAG_NAME"))

    def __tag_value(self, mb, tag, handle):
        return str(mb.tag_get_data(tag, handle).flat[0])

    def __visited_any_volume(self, volumes, name):
        for h in volumes:
            if h in self.__visited:
                pkdlog(f"skipping volume used in multiple groups: {h} {name}")
                return True
            self.__visited.add(h)
        return False

    def __volumes(self, mb, name, group):
        v = [h for h in mb.get_entities_by_handle(group)]
        if self.__visited_any_volume(v, name):
            return None
        return v


class MoabGroupExtractor:
    __DATA_DIR = "data"
    __VTI_TEMPLATE = PKDict(
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
                basepath=__DATA_DIR,
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
                basepath=__DATA_DIR,
                id=None,
            ),
            size=None,
        ),
        metadata=PKDict(
            name=None,
        ),
    )

    def __init__(self, collector):
        self.__items = []
        for g in collector.groups:
            self.__items.append(
                PKDict(
                    dagmc_filename=collector.dagmc_filename,
                    vol_id=g.vol_id,
                    volumes=g.volumes,
                    processor=self,
                )
            )
        # process longest volume sets first
        self.__items.sort(key=lambda v: -len(v.volumes))

    def get_items(self):
        return self.__items

    def process_item(self, item):
        self.__write_vti(item.vol_id, self.__get_points_and_polys(item))

    def __array_from_list(self, arr, arr_type):
        res = array.array(arr_type)
        res.fromlist(arr)
        return res

    def __get_points_and_polys(self, item):
        mb = pymoab.core.Core()
        mb.load_file(item.dagmc_filename)
        verticies = pymoab.rng.Range()
        triangles = pymoab.rng.Range()
        for h in item.volumes:
            self.__get_verticies_and_triangles(mb, h, verticies, triangles)
        m = {}
        for i, v in enumerate(verticies):
            m[v] = i
        polys = []
        for t in triangles:
            polys.append(3)
            polys += [m[vert] for vert in mb.get_connectivity(t)]
        return PKDict(
            points=self.__array_from_list(list(mb.get_coords(verticies)), "f"),
            polys=self.__array_from_list(polys, "I"),
        )

    def __get_verticies_and_triangles(
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
            self.__get_verticies_and_triangles(mb, c, verticies, triangles, visited)

    def __write_vti(self, vol_id, geometry):
        pkio.unchecked_remove(vol_id)
        p = pkio.mkdir_parent(f"{vol_id}/{MoabGroupExtractor.__DATA_DIR}")
        vti = copy.deepcopy(MoabGroupExtractor.__VTI_TEMPLATE)
        vti.metadata.name = f"{vol_id}.vtp"
        fns = []
        for n in ("polys", "points"):
            fn = str(uuid.uuid1()).replace("-", "")
            with open(str(p.join(fn)), "wb") as f:
                geometry[n].tofile(f)
            vti[n].ref.id = fn
            vti[n].size = int(len(geometry[n]))
            fns.append(f"{MoabGroupExtractor.__DATA_DIR}/{fn}")
        with sirepo.util.write_zip(f"{vol_id}.zip") as f:
            f.writestr("index.json", json.dumps(vti))
            for fn in fns:
                f.write(f"{vol_id}/{fn}", arcname=fn)
        pkio.unchecked_remove(vol_id)


def extract_dagmc(dagmc_filename):
    gc = MoabGroupCollector(dagmc_filename)
    sirepo.mpi.multiprocessing_pool_map(MoabGroupExtractor(gc))
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
    sirepo.template.cloudmc.extract_report_data(pkio.py_path(cfg_dir), data)
