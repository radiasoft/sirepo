# -*- coding: utf-8 -*-
"""Utilities and wrappers for calling Radia functions

:copyright: Copyright (c) 2017-2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import numpy
import radia
import sys


from numpy import linalg
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp

AXES = ["x", "y", "z"]

AXIS_VECTORS = PKDict(
    x=numpy.array([1.0, 0, 0]),
    y=numpy.array([0, 1.0, 0]),
    z=numpy.array([0, 0, 1.0]),
)


FIELD_TYPE_MAG_A = "A"
FIELD_TYPE_MAG_B = "B"
FIELD_TYPE_MAG_H = "H"
FIELD_TYPE_MAG_I = "I"
FIELD_TYPE_MAG_J = "J"
FIELD_TYPE_MAG_M = "M"
FIELD_TYPES = [FIELD_TYPE_MAG_M]
POINT_FIELD_TYPES = [
    FIELD_TYPE_MAG_B,
    FIELD_TYPE_MAG_A,
    FIELD_TYPE_MAG_H,
    FIELD_TYPE_MAG_J,
]
FIELD_TYPES.extend(POINT_FIELD_TYPES)
INTEGRABLE_FIELD_TYPES = [FIELD_TYPE_MAG_B, FIELD_TYPE_MAG_H, FIELD_TYPE_MAG_I]

# these might be available from radia
FIELD_UNITS = PKDict(
    {
        FIELD_TYPE_MAG_A: "T mm",
        FIELD_TYPE_MAG_B: "T",
        FIELD_TYPE_MAG_H: "A/m",
        FIELD_TYPE_MAG_J: "A/m^2",
        FIELD_TYPE_MAG_M: "A/m",
    }
)

_MU_0 = 4 * numpy.pi / 1e7
_ZERO = [0, 0, 0]


class MPI:
    def __init__(self):
        # Null op for when not in MPI
        self._uti_mpi = lambda x: None
        try:
            import mpi4py.MPI

            if mpi4py.MPI.COMM_WORLD.Get_size() > 1:
                self._uti_mpi = radia.UtiMPI
        except Exception:
            pass

    def __enter__(self):
        self._uti_mpi("in")
        return self

    def __exit__(self, t, value, traceback):
        self._uti_mpi("off")

    def barrier(self):
        self._uti_mpi("barrier")


def _apply_bevel(g_id, **kwargs):
    d = PKDict(kwargs)
    dirs = _calc_directions(d.cutAxis)

    e = int(d.edge)
    w_offset, h_offset = _bevel_offsets_for_axes(e, **dirs, **kwargs)

    v = w_offset - h_offset
    vx2 = numpy.dot(w_offset, w_offset)
    vg2 = numpy.dot(h_offset, h_offset)
    v2 = numpy.dot(v, v)

    plane = int(d.cutRemoval) * (
        numpy.array(dirs.widthDir) * [-1, 1, 1, -1][e] * numpy.sqrt(vg2 / v2)
        + numpy.array(dirs.heightDir) * [1, 1, -1, -1][e] * numpy.sqrt(vx2 / v2)
    )

    return _apply_cut(
        g_id,
        cutPoint=(_corner_for_axes(e, **dirs, **kwargs) + w_offset).tolist(),
        cutPlane=plane.tolist(),
    )


def _apply_clone(g_id, xform):
    xform = PKDict(xform)
    # start with 'identity'
    total_xform = radia.TrfTrsl([0, 0, 0])
    for clone_xform in xform.transforms:
        cxf = PKDict(clone_xform)
        if cxf.type == "translate":
            total_xform = radia.TrfCmbL(total_xform, radia.TrfTrsl(cxf.distance))
        if cxf.type == "rotate":
            total_xform = radia.TrfCmbL(
                total_xform,
                radia.TrfRot(
                    cxf.center,
                    cxf.axis,
                    numpy.pi * float(cxf.angle) / 180.0,
                ),
            )
    if xform.alternateFields != "0":
        total_xform = radia.TrfCmbL(total_xform, radia.TrfInv())
    radia.TrfMlt(g_id, total_xform, xform.numCopies + 1)


def _apply_cut(g_id, **kwargs):
    d = PKDict(kwargs)
    p = d.cutPoint
    if d.get("useObjectCenter", "0") == "1":
        p = (numpy.array(p) + numpy.array(d.obj_center)).tolist()

    # args are object id, point in plane, plane normal - returns array of new ids
    return radia.ObjCutMag(
        g_id,
        p,
        d.cutPlane,
        "Frame->Lab",
    )[0]


def _apply_fillet(g_id, **kwargs):
    d = PKDict(kwargs)

    dirs = _calc_directions(d.cutAxis)
    cut_amts = PKDict(
        amountVert=d.radius,
        amountHoriz=d.radius,
    )
    g_id = _apply_bevel(
        g_id,
        cutRemoval=1,
        **cut_amts,
        **kwargs,
    )
    w_offset, h_offset = _bevel_offsets_for_axes(
        int(d.edge), **dirs, **cut_amts, **kwargs
    )
    ctr = (
        _corner_for_axes(int(d.edge), **dirs, **kwargs)
        + w_offset
        + h_offset
        - (numpy.array(d.obj_size) / 2) * dirs.lenDir
    )
    c_id = _build_cylinder(
        center=ctr,
        extrusionAxis=d.cutAxis,
        segmentation="cyl",
        size=d.obj_size,
        **kwargs,
    )
    c_id = _apply_bevel(c_id, cutRemoval=-1, **cut_amts, **kwargs)
    return build_container([g_id, c_id])


def _apply_material(g_id, **kwargs):
    def _radia_material(**kwargs):
        d = PKDict(kwargs)
        if d.material == "custom":
            return radia.MatSatIsoTab(
                [
                    [_MU_0 * d.h_m_curve[i][0], d.h_m_curve[i][1]]
                    for i in range(len(d.h_m_curve))
                ]
            )
        if d.material == "nonlinear":
            f = d.materialFormula
            return radia.MatSatIsoFrm(f[0:2], f[2:4], f[4:6])
        return radia.MatStd(d.material, d.remanentMag)

    radia.MatApl(g_id, _radia_material(**kwargs))


def _apply_modification(g_id, **kwargs):
    return PKDict(
        objectBevel=_apply_bevel,
        objectCut=_apply_cut,
        objectFillet=_apply_fillet,
    )[kwargs.get("type")](g_id, **kwargs)


def _apply_rotation(g_id, xform):
    xform = PKDict(xform)
    radia.TrfOrnt(
        g_id,
        radia.TrfRot(
            (
                _geom_bounds(g_id)
                if xform.get("useObjectCenter", "0") == "1"
                else xform
            ).center,
            xform.axis,
            numpy.pi * float(xform.angle) / 180.0,
        ),
    )


def _apply_segments(g_id, **kwargs):
    d = PKDict(kwargs)
    if d.segments and any([s > 1 for s in d.segments]):
        if d.segmentation == "pln":
            radia.ObjDivMag(g_id, d.segments)
        # cylindrical division does not seem to work properly in the local frame if the
        # axis is not "x" and the center is not [0, 0, 0]
        if d.segmentation == "cyl":
            p = (
                d.center
                if d.segmentationCylUseObjectCenter == "1"
                else d.segmentationCylPoint
            )
            # The radial segment number is "number of segments between 0 and the given radius",
            # except when it is 1 in which case it's "none". We ignore it and prompt the user
            # for the radial size. Since 1 is special we say "2 segments in twice the radius"
            radia.ObjDivMag(
                g_id,
                [2, d.segments[1], d.segments[2]],
                d.segmentation,
                [
                    p,
                    AXIS_VECTORS[d.segmentationCylAxis].tolist(),
                    (
                        2.0
                        * d.segmentationCylRadius
                        * AXIS_VECTORS[next_axis(d.segmentationCylAxis)]
                        + p
                    ).tolist(),
                    d.segmentationCylRatio,
                ],
                "Frame->Lab",
            )


def _apply_symmetry(g_id, xform):
    xform = PKDict(xform)
    plane = xform.symmetryPlane
    point = xform.symmetryPoint
    if xform.symmetryType == "parallel":
        radia.TrfZerPara(g_id, point, plane)
    if xform.symmetryType == "perpendicular":
        radia.TrfZerPerp(g_id, point, plane)


def _apply_translation(g_id, xform):
    xform = PKDict(xform)
    radia.TrfOrnt(
        g_id,
        radia.TrfTrsl(xform.distance),
    )


def _bevel_offsets_for_axes(edge_index, **kwargs):
    d = PKDict(kwargs)
    return (
        d.amountHoriz * numpy.array(d.widthDir) * [1, -1, -1, 1][edge_index],
        d.amountVert * numpy.array(d.heightDir) * [-1, -1, 1, 1][edge_index],
    )


def _build_cuboid(**kwargs):
    d = PKDict(kwargs)
    return radia.ObjRecMag(d.center, d.size, d.magnetization)


def _build_stl(**kwargs):
    d = PKDict(kwargs)
    g_id = radia.ObjPolyhdr(
        d.stlVertices, (numpy.array(d.stlFaces) + 1).tolist(), d.magnetization
    )
    if d.preserveVerticesOnImport == "0":
        center = [x - d.stlBoundsCenter[i] for i, x in enumerate(d.center)]
        radia.TrfOrnt(g_id, radia.TrfTrsl([center[0], center[1], center[2]]))
    return g_id


def _build_cylinder(**kwargs):
    d = PKDict(kwargs)
    return radia.ObjCylMag(
        d.center,
        d.radius,
        d.size[axes_index(d.extrusionAxis)],
        d.numSides,
        d.extrusionAxis,
        d.magnetization,
    )


def _build_racetrack(**kwargs):
    d = PKDict(kwargs)
    return radia.ObjRaceTrk(
        d.center,
        d.radii,
        d.sides,
        d.height,
        d.numSegments,
        d.currentDensity,
        d.fieldCalc,
        d.axis,
    )


def _calc_directions(axis):
    w = next_axis(axis)
    h = next_axis(w)
    return PKDict(
        lenDir=AXIS_VECTORS[axis],
        widthDir=AXIS_VECTORS[w],
        heightDir=AXIS_VECTORS[h],
    )


def _clone_with_translation(g_id, num_copies, distance, alternate_fields):
    xf = radia.TrfTrsl(distance)
    if alternate_fields:
        xf = radia.TrfCmbL(xf, radia.TrfInv())
    radia.TrfMlt(g_id, xf, num_copies + 1)


# edge_index starts at the top left - meaning minimum width coordinate and maximum height
# coordinate in the plane defined by the length direction - proceeding clockwise
def _corner_for_axes(edge_index, **kwargs):
    d = PKDict(kwargs)
    l = numpy.array(d.lenDir)
    h = numpy.array(d.heightDir)
    w = numpy.array(d.widthDir)
    return (
        numpy.array(d.obj_center)
        + numpy.array(d.obj_size)
        / 2
        * [-w + h + l, w + h + l, w - h + l, -w - h + l][edge_index]
    )


def _extrude(**kwargs):
    d = PKDict(kwargs)
    b = AXIS_VECTORS[d.extrusionAxis]
    return radia.ObjMltExtTri(
        numpy.sum(b * d.center),
        numpy.sum(b * d.size),
        d.points,
        numpy.full((len(d.points), 2), [1, 1]).tolist(),
        d.extrusionAxis,
        d.magnetization,
        (
            f"TriAreaMax->{0.125 * d.area * (1.04 - d.triangulationLevel)}"
            if d.triangulationLevel > 0
            else ""
        ),
    )


def _geom_bounds(g_id):
    bnds = radia.ObjGeoLim(g_id)
    return PKDict(
        center=[bnds[2 * i] + (bnds[2 * i + 1] - bnds[2 * i]) / 2 for i in range(3)],
        size=[abs(bnds[2 * i + 1] - bnds[2 * i]) for i in range(3)],
    )


def apply_color(g_id, color):
    radia.ObjDrwAtr(g_id, color)


def apply_transform(g_id, **kwargs):
    PKDict(
        cloneTransform=_apply_clone,
        symmetryTransform=_apply_symmetry,
        rotate=_apply_rotation,
        translate=_apply_translation,
    )[kwargs.get("type")](g_id, kwargs)


def axes_index(axis):
    return AXES.index(axis)


def build_container(g_ids):
    return radia.ObjCnt(g_ids)


def build_object(**kwargs):
    d = PKDict(kwargs)
    t = d.type
    g_id = PKDict(
        cee=_extrude,
        cuboid=_build_cuboid,
        cylinder=_build_cylinder,
        ell=_extrude,
        extrudedPoints=_extrude,
        jay=_extrude,
        racetrack=_build_racetrack,
        stl=_build_stl,
    )[t](**kwargs)
    # coils get no extra handling
    if t == "racetrack":
        return g_id
    _apply_segments(g_id, **kwargs)
    _apply_material(g_id, **kwargs)
    for m in d.get("modifications", []):
        g_id = _apply_modification(
            g_id,
            magnetization=d.magnetization,
            material=d.material,
            obj_center=d.center,
            obj_size=d.size,
            remanentMag=d.remanentMag,
            h_m_curve=d.h_m_curve,
            **m,
        )
    return g_id


def dump(g_id):
    return radia.UtiDmp(g_id, "asc")


def dump_bin(g_id):
    return radia.UtiDmp(g_id, "bin")


# only i (?), m, h
def field_integral(g_id, f_type, p1, p2):
    return radia.FldInt(g_id, "inf", f_type, p1, p2)


def free_symmetries(g_id):
    return radia.ObjDpl(g_id, "FreeSym->True")


def geom_to_data(g_id, name=None, divide=True):
    def _to_pkdict(d):
        if not isinstance(d, dict):
            return d
        rv = PKDict()
        for k, v in d.items():
            rv[k] = _to_pkdict(v)
        return rv

    n = (name if name is not None else str(g_id)) + ".Geom"
    pd = PKDict(name=n, id=g_id, data=[])
    d = _to_pkdict(radia.ObjDrwVTK(g_id, "Axes->No"))
    d.update(_geom_bounds(g_id))
    n_verts = len(d.polygons.vertices)
    c = radia.ObjCntStuf(g_id)
    l = len(c)
    if not divide or l == 0:
        d.id = g_id
        pd.data = [d]
    else:
        d_arr = []
        n_s_verts = 0
        # for g in get_geom_tree(g_id):
        for g in c:
            # for fully recursive array
            # for g in get_all_geom(geom):
            s_d = _to_pkdict(radia.ObjDrwVTK(g, "Axes->No"))
            s_d.update(_geom_bounds(g))
            n_s_verts += len(s_d.polygons.vertices)
            s_d.id = g
            d_arr.append(s_d)
        # if the number of vertices of the container is more than the total
        # across its elements, a symmetry or other "additive" transformation has
        # been applied and we cannot get at the individual elements
        if n_verts > n_s_verts:
            d.id = g_id
            d_arr = [d]
        pd.data = d_arr
    pd.bounds = radia.ObjGeoLim(g_id)
    return pd


def get_all_geom(g_id):
    g_arr = []
    for g in radia.ObjCntStuf(g_id):
        if len(radia.ObjCntStuf(g)) > 0:
            g_arr.extend(get_all_geom(g))
        else:
            g_arr.append(g)
    return g_arr


def get_geom_tree(g_id, recurse_depth=0):
    g_arr = []
    for g in radia.ObjCntStuf(g_id):
        if len(radia.ObjCntStuf(g)) > 0:
            if recurse_depth > 0:
                g_arr.extend(get_geom_tree(g, recurse_depth=recurse_depth - 1))
            else:
                g_arr.extend([g])
        else:
            g_arr.append(g)
    return g_arr


# Radia expects the electron to travel in the y direction so we must rotate all the
# fields such that the simulation's beam axis points along y.
# The resulting trajectory is of the form
#   [[y0, x0, dx/dy0, z0, dz/dy0], [y1, x1, dx/dy1, z1, dz/dy1],...]
# where x/z is the width/height direction and y is the beam direction
def get_electron_trajectory(g_id, **kwargs):
    d = PKDict(kwargs)
    axis = d.rotation.as_rotvec(degrees=True)
    angle = numpy.linalg.norm(axis)
    # Identity Rotations produce a degenerate (all 0s) axis
    if any(axis):
        _apply_rotation(
            g_id,
            PKDict(
                center="0,0,0",
                axis=axis,
                angle=angle,
            ),
        )
    p = d.rotation.apply(d.pos)
    a = d.rotation.apply(d.angles)
    t = radia.FldPtcTrj(
        g_id,
        d.energy,
        [p[0], a[0], p[2], a[2]],
        [p[1], d.y_final],
        d.num_points,
    )
    tt = numpy.array(t).T
    tcx = d.rotation.inv().apply(numpy.array([tt[1], tt[0], tt[3]]).T).T
    # ignore angles for now
    return tcx


# path is *flattened* array of positions in space ([x1, y1, z1,...xn, yn, zn])
def get_field(g_id, f_type, path):
    if len(path) == 0:
        return []
    pv_arr = []
    p = numpy.reshape(path, (-1, 3)).tolist()
    b = []
    # get every component (meaning e.g. passing 'B' and not 'Bx' etc.)
    f = radia.Fld(g_id, f_type, path)
    # a dummy value returned by parallel radia
    if f == 0:
        f = numpy.zeros(len(path))
    b.extend(f)
    b = numpy.reshape(b, (-1, 3)).tolist()
    for p_idx, pt in enumerate(p):
        pv_arr.append([pt, b[p_idx]])
    return pv_arr


def get_magnetization(g_id):
    return radia.ObjM(g_id)


def kick_map(
    g_id,
    begin,
    dir_long,
    num_periods,
    period_length,
    dir_trans,
    range_trans_1,
    num_pts_trans_1,
    range_trans_2,
    num_pts_trans_2,
):
    km = radia.FldFocKickPer(
        g_id,
        begin,
        dir_long,
        period_length,
        num_periods,
        dir_trans,
        range_trans_1,
        num_pts_trans_1,
        range_trans_2,
        num_pts_trans_2,
    )
    return km


def load_bin(data):
    return radia.UtiDmpPrs(data)


def multiply_vector_by_matrix(v, m):
    return numpy.array(m).dot(numpy.array(v)).tolist()


def new_geom_object():
    return PKDict(
        lines=PKDict(colors=[], lengths=[], vertices=[]),
        polygons=PKDict(colors=[], lengths=[], vertices=[]),
        vectors=PKDict(directions=[], magnitudes=[], vertices=[]),
    )


def next_axis(axis):
    return AXES[(AXES.index(axis) + 1) % len(AXES)]


def reset():
    return radia.UtiDelAll()


def solve(g_id, prec, max_iter, solve_method):
    return radia.Solve(g_id, float(prec), int(max_iter), int(solve_method))


def vector_field_to_data(g_id, name, pv_arr, units):
    # format is [[[px, py, pz], [vx, vy, vx]], ...]
    # UNLESS only one element?
    # convert to webGL object
    if len(numpy.shape(pv_arr)) == 2:
        pv_arr = [pv_arr]
    v_data = new_geom_object()
    v_data.id = g_id
    v_data.vectors.lengths = []
    v_data.vectors.colors = []
    v_max = 0.0
    v_min = sys.float_info.max
    for i in range(len(pv_arr)):
        p = pv_arr[i][0]
        v = pv_arr[i][1]
        n = numpy.linalg.norm(v)
        v_max = max(v_max, n)
        v_min = min(v_min, n)
        nv = (numpy.array(v) / (n if n > 0 else 1.0)).tolist()
        v_data.vectors.vertices.extend(p)
        v_data.vectors.directions.extend(nv)
        v_data.vectors.magnitudes.append(n)
    v_data.vectors.range = [v_min, v_max]
    v_data.vectors.units = units

    return PKDict(
        name=name + ".Field", id=g_id, data=[v_data], bounds=radia.ObjGeoLim(g_id)
    )
