# -*- coding: utf-8 -*-
"""Utilities and wrappers for calling Radia functions

:copyright: Copyright (c) 2017-2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import numpy
import radia
import sirepo.util
import sys


from numpy import linalg
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp

AXES = ["x", "y", "z"]

AXIS_VECTORS = PKDict(
    x=numpy.array([1, 0, 0]),
    y=numpy.array([0, 1, 0]),
    z=numpy.array([0, 0, 1]),
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


def _apply_clone(g_id, xform):
    xform = PKDict(xform)
    # start with 'identity'
    xf = radia.TrfTrsl([0, 0, 0])
    for clone_xform in xform.transforms:
        cxf = PKDict(clone_xform)
        if cxf.model == "translateClone":
            txf = radia.TrfTrsl(
                sirepo.util.split_comma_delimited_string(cxf.distance, float)
            )
            xf = radia.TrfCmbL(xf, txf)
        if cxf.model == "rotateClone":
            rxf = radia.TrfRot(
                sirepo.util.split_comma_delimited_string(cxf.center, float),
                sirepo.util.split_comma_delimited_string(cxf.axis, float),
                numpy.pi * float(cxf.angle) / 180.0,
            )
            xf = radia.TrfCmbL(xf, rxf)
    if xform.alternateFields != "0":
        xf = radia.TrfCmbL(xf, radia.TrfInv())
    radia.TrfMlt(g_id, xf, xform.numCopies + 1)


def _apply_rotation(g_id, xform):
    xform = PKDict(xform)
    radia.TrfOrnt(
        g_id,
        radia.TrfRot(
            sirepo.util.split_comma_delimited_string(xform.center, float),
            sirepo.util.split_comma_delimited_string(xform.axis, float),
            numpy.pi * float(xform.angle) / 180.0,
        ),
    )


def _apply_segments(g_id, segments, seg_type="pln", **kwargs):
    if segments and any([s > 1 for s in segments]):
        if seg_type == "pln":
            radia.ObjDivMag(g_id, segments)
        # cylindrical division does not seem to work properly in the local frame if the
        # axis is not "x" and the center is not [0, 0, 0]
        if seg_type == "cyl":
            d = PKDict(kwargs)
            radia.ObjDivMag(
                g_id,
                segments,
                seg_type,
                [
                    d.center,
                    d.axis,
                    d.perp_axis,
                    1.0,
                ],
                "Frame->Lab",
            )


def _apply_symmetry(g_id, xform):
    xform = PKDict(xform)
    plane = sirepo.util.split_comma_delimited_string(xform.symmetryPlane, float)
    point = sirepo.util.split_comma_delimited_string(xform.symmetryPoint, float)
    if xform.symmetryType == "parallel":
        radia.TrfZerPara(g_id, point, plane)
    if xform.symmetryType == "perpendicular":
        radia.TrfZerPerp(g_id, point, plane)


def _apply_translation(g_id, xform):
    xform = PKDict(xform)
    radia.TrfOrnt(
        g_id,
        radia.TrfTrsl(sirepo.util.split_comma_delimited_string(xform.distance, float)),
    )


def axes_index(axis):
    return AXES.index(axis)


def _bevel_offsets_for_axes(edge_index, **kwargs):
    d = PKDict(kwargs)
    h = numpy.array(d.heightDir)
    w = numpy.array(d.widthDir)
    return (
        d.amountHoriz * w * [1, -1, -1, 1][edge_index],
        d.amountVert * h * [-1, -1, 1, 1][edge_index],
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
        numpy.array(d.center)
        + numpy.array(d.size)
        / 2
        * [-w + h + l, w + h + l, w - h + l, -w - h + l][edge_index]
    )


def _geom_bounds(g_id):
    bnds = radia.ObjGeoLim(g_id)
    return PKDict(
        center=[0.5 * (bnds[i + 1] + bnds[i]) for i in range(3)],
        size=[abs(bnds[i + 1] - bnds[i]) for i in range(3)],
    )


def _radia_material(material_type, magnetization_magnitude, h_m_curve):
    if material_type == "custom":
        return radia.MatSatIsoTab(
            [[_MU_0 * h_m_curve[i][0], h_m_curve[i][1]] for i in range(len(h_m_curve))]
        )
    return radia.MatStd(material_type, magnetization_magnitude)


_TRANSFORMS = PKDict(
    cloneTransform=_apply_clone,
    symmetryTransform=_apply_symmetry,
    rotate=_apply_rotation,
    translate=_apply_translation,
)


def apply_bevel(g_id, **kwargs):
    d = PKDict(kwargs)

    e = int(d.edge)
    w_offset, h_offset = _bevel_offsets_for_axes(e, **kwargs)

    v = w_offset - h_offset
    vx2 = numpy.dot(w_offset, w_offset)
    vg2 = numpy.dot(h_offset, h_offset)
    v2 = numpy.dot(v, v)

    plane = int(d.cutRemoval) * (
        numpy.array(d.widthDir) * [-1, 1, 1, -1][e] * numpy.sqrt(vg2 / v2)
        + numpy.array(d.heightDir) * [1, 1, -1, -1][e] * numpy.sqrt(vx2 / v2)
    )

    # object id, plane normal, point in plane - returns a new id in an array for some reason
    return radia.ObjCutMag(
        g_id,
        (_corner_for_axes(e, **kwargs) + w_offset).tolist(),
        plane.tolist(),
        "Frame->Lab",
    )[0]


def apply_color(g_id, color):
    radia.ObjDrwAtr(g_id, color)


def apply_fillet(g_id, **kwargs):
    d = PKDict(kwargs)

    w = next_axis(d.cutAxis)
    h = next_axis(w)
    dirs = PKDict(
        lenDir=AXIS_VECTORS[d.cutAxis],
        widthDir=AXIS_VECTORS[w],
        heightDir=AXIS_VECTORS[h],
    )
    cut_amts = PKDict(
        amountVert=d.radius,
        amountHoriz=d.radius,
    )
    g_id = apply_bevel(
        g_id,
        cutRemoval=1,
        **dirs,
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
        - (numpy.array(d.size) / 2) * dirs.lenDir
    )
    c_id = build_cylinder(
        extrusion_axis=d.cutAxis,
        center=ctr,
        num_sides=d.numSides,
        seg_type="pln",
        **{k: v for k, v in kwargs.items() if k != "center"},
    )
    c_id = apply_bevel(c_id, cutRemoval=-1, **dirs, **cut_amts, **kwargs)
    return build_container([g_id, c_id])


def multiply_vector_by_matrix(v, m):
    return numpy.array(m).dot(numpy.array(v)).tolist()


def apply_transform(g_id, xform):
    _TRANSFORMS[xform["model"]](g_id, xform)


def build_container(g_ids):
    return radia.ObjCnt(g_ids)


def build_cuboid(**kwargs):
    d = PKDict(kwargs)
    g_id = radia.ObjRecMag(d.center, d.size, d.magnetization)
    _apply_segments(g_id, d.segments)
    radia.MatApl(g_id, _radia_material(d.material, d.rem_mag, d.h_m_curve))
    return g_id


def build_cylinder(**kwargs):
    d = PKDict(kwargs)
    axis = d.extrusion_axis
    g_id = radia.ObjCylMag(
        d.center,
        d.radius,
        d.size[axes_index(axis)],
        d.num_sides,
        d.extrusion_axis,
        d.magnetization,
    )
    _apply_segments(
        g_id,
        d.segments,
        seg_type=d.get("seg_type", "cyl"),
        center=d.center,
        axis=AXIS_VECTORS[axis].tolist(),
        perp_axis=(d.radius * AXIS_VECTORS[next_axis(axis)] + d.center).tolist(),
    )
    radia.MatApl(g_id, _radia_material(d.material, d.rem_mag, d.h_m_curve))
    return g_id


def build_racetrack(**kwargs):
    d = PKDict(kwargs)
    return radia.ObjRaceTrk(
        d.center, d.radii, d.sides, d.height, d.num_segs, d.curr_density, d.calc, d.axis
    )


def dump(g_id):
    return radia.UtiDmp(g_id, "asc")


def dump_bin(g_id):
    return radia.UtiDmp(g_id, "bin")


def extrude(**kwargs):
    d = PKDict(kwargs)
    b = AXIS_VECTORS[d.extrusion_axis]
    g_id = radia.ObjMltExtTri(
        numpy.sum(b * d.center),
        numpy.sum(b * d.size),
        d.points,
        numpy.full((len(d.points), 2), [1, 1]).tolist(),
        d.extrusion_axis,
        d.magnetization,
        f"TriAreaMax->{0.125 * d.area * (1.04 - d.t_level)}" if d.t_level > 0 else "",
    )
    _apply_segments(g_id, d.segments)
    radia.MatApl(g_id, _radia_material(d.material, d.rem_mag, d.h_m_curve))
    return g_id


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
                axis=sirepo.util.to_comma_delimited_string(axis),
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
