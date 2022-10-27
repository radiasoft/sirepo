# -*- coding: utf-8 -*-
"""Trimesh and Radia stl import test

:copyright: Copyright (c) 2017-2022 RadiaSoft LLC. All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

RAW_VERTICES = [[0, 0, 0], [1, 1, 0], [0, 1, 0], [0.5, 0.5, 1]]
RAW_FACES = [[1, 2, 3], [1, 2, 4], [1, 4, 3], [4, 2, 3]]

RAW_EXPECTED = [[0.0, 1.0, 0.0],
 [1.0, 1.0, 0.0],
 [0.0, 0.0, 0.0],
 [0.0, 0.0, 0.0],
 [1.0, 1.0, 0.0],
 [0.5, 0.5, 1.0],
 [0.0, 0.0, 0.0],
 [0.5, 0.5, 1.0],
 [0.0, 1.0, 0.0],
 [0.5, 0.5, 1.0],
 [1.0, 1.0, 0.0],
 [0.0, 1.0, 0.0]]

def _create_mesh(filePath):
    import trimesh
    
    f = open(filePath)
    mesh = trimesh.load(f, file_type='stl', force='mesh', process=True)
    f.close()
    return mesh

def _convex_check(mesh):
    import trimesh
    
    if trimesh.convex.is_convex(mesh) == False:
        return "concave"
    return "convex"

def test_raw():
    import radia
    import numpy
    from pykern.pkunit import pkeq
    
    g_id = radia.ObjPolyhdr(RAW_VERTICES, RAW_FACES)
    d = radia.ObjDrwVTK(g_id, "Axes->No")
    actual = numpy.array([round(x, 6) for x in d["polygons"]["vertices"]]).reshape(-1, 3).tolist()
    pkeq(RAW_EXPECTED, actual)
    
def test_import():
    from pykern import pkunit
    from pykern.pkunit import pkeq
    
    actual = []
    for d in pkunit.case_dirs():
        with pkunit.ExceptToFile():
            path = d.join("in.stl")
            mesh = _create_mesh(path)
            actual.append(_convex_check(mesh))
    pkeq(['convex', 'concave'], actual)
    