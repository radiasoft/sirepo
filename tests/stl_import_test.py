"""Trimesh and Radia stl import test

:copyright: Copyright (c) 2017-2022 RadiaSoft LLC. All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_RAW_VERTICES = [[0, 0, 0], [1, 1, 0], [0, 1, 0], [0.5, 0.5, 1]]
_RAW_FACES = [[1, 2, 3], [1, 2, 4], [1, 4, 3], [4, 2, 3]]

_RAW_EXPECTED = [
    [0.0, 1.0, 0.0],
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
    [0.0, 1.0, 0.0],
]


def _create_mesh(file_path):
    import trimesh

    with open(file_path) as f:
        return trimesh.load(f, file_type="stl", force="mesh", process=True)


def _convex_check(mesh):
    import trimesh

    return trimesh.convex.is_convex(mesh)


def _is_binary(file_path):
    textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
    return is_binary_string(open(file_path, "rb").read(1024))


def test_binary():
    from pykern import pkunit
    from pykern.pkunit import pkeq

    actual = [
        _is_binary(pkunit.data_dir().join("file_type/ascii.stl")),
        _is_binary(pkunit.data_dir().join("file_type/binary.stl")),
    ]
    pkeq([False, True], actual)


def test_raw():
    import radia
    import numpy
    from pykern.pkunit import pkeq

    d = radia.ObjDrwVTK(radia.ObjPolyhdr(_RAW_VERTICES, _RAW_FACES), "Axes->No")
    actual = (
        numpy.array([round(x, 6) for x in d["polygons"]["vertices"]])
        .reshape(-1, 3)
        .tolist()
    )
    pkeq(_RAW_EXPECTED, actual)


def test_import():
    from pykern import pkunit
    from pykern.pkunit import pkeq

    actual = []
    for d in pkunit.case_dirs():
        with pkunit.ExceptToFile():
            actual.append(_convex_check(_create_mesh(d.join("in.stl"))))
    pkeq([True, False], actual)
