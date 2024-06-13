"""PyTest for :mod:`sirepo.template.srw`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_srw_resize_3d():
    from pykern import pkunit
    from sirepo.template import srw

    MAX = srw._CANVAS_MAX_SIZE

    for t in (
        [(100, 100), (100, 100)],
        [(100, MAX + 1), (100, MAX)],
        [(MAX + 1, 100), (MAX, 100)],
        [(400, 400), (400, 400)],
        [(MAX, MAX), (4472, 4472)],
        [(MAX, MAX * 2), (3162, 6324)],
        [(MAX * 2, MAX), (6324, 3162)],
        [(MAX + 1, 300), (MAX, 300)],
        [(300, MAX + 1), (300, MAX)],
        [(400, MAX), (349, 57242)],
        [(MAX, 400), (57242, 349)],
        [(400, 1e6), (305, MAX)],
        [(1e6, 400), (MAX, 305)],
        [(MAX * 10, MAX), (14142, 1414)],
        [(MAX, MAX * 10), (1414, 14142)],
    ):
        x, y = srw._resize_mesh_dimensions(t[0][0], t[0][1])
        assert x * y <= srw._MAX_REPORT_POINTS
        pkunit.pkeq((x, y), t[1])
