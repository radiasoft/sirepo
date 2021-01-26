import numpy
import radia
import re
import sirepo.util
import sys

from numpy import linalg
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp

FIELD_TYPE_MAG_A = 'A'
FIELD_TYPE_MAG_B = 'B'
FIELD_TYPE_MAG_H = 'H'
FIELD_TYPE_MAG_I = 'I'
FIELD_TYPE_MAG_J = 'J'
FIELD_TYPE_MAG_M = 'M'
FIELD_TYPES = [FIELD_TYPE_MAG_M]
POINT_FIELD_TYPES = [
    FIELD_TYPE_MAG_B, FIELD_TYPE_MAG_A, FIELD_TYPE_MAG_H, FIELD_TYPE_MAG_J
]
FIELD_TYPES.extend(POINT_FIELD_TYPES)
INTEGRABLE_FIELD_TYPES = [FIELD_TYPE_MAG_B, FIELD_TYPE_MAG_H, FIELD_TYPE_MAG_I]

# these might be available from radia
FIELD_UNITS = PKDict({
    FIELD_TYPE_MAG_A: 'T mm',
    FIELD_TYPE_MAG_B: 'T',
    FIELD_TYPE_MAG_H: 'A/m',
    FIELD_TYPE_MAG_J: 'A/m^2',
    FIELD_TYPE_MAG_M: 'A/m',
})


_MU_0 = 4 * numpy.pi / 1e7
_ZERO = [0, 0, 0]


def _apply_clone(g_id, xform):
    xform = PKDict(xform)
    # start with 'identity'
    xf = radia.TrfTrsl([0, 0, 0])
    for clone_xform in xform.transforms:
        cxf = PKDict(clone_xform)
        if cxf.model == 'translateClone':
            txf = radia.TrfTrsl(sirepo.util.split_comma_delimited_string(cxf.distance, float))
            xf = radia.TrfCmbL(xf, txf)
        if cxf.model == 'rotateClone':
            rxf = radia.TrfRot(
                sirepo.util.split_comma_delimited_string(cxf.center, float),
                sirepo.util.split_comma_delimited_string(cxf.axis, float),
                numpy.pi * float(cxf.angle) / 180.
            )
            xf = radia.TrfCmbL(xf, rxf)
    if xform.alternateFields != '0':
        xf = radia.TrfCmbL(xf, radia.TrfInv())
    radia.TrfMlt(g_id, xf, xform.numCopies + 1)


def _apply_rotation(g_id, xform):
    xform = PKDict(xform)
    radia.TrfOrnt(
        g_id,
        radia.TrfRot(
            sirepo.util.split_comma_delimited_string(xform.center, float),
            sirepo.util.split_comma_delimited_string(xform.axis, float),
            numpy.pi * float(xform.angle) / 180.
        )
    )


def _apply_symmetry(g_id, xform):
    xform = PKDict(xform)
    plane = sirepo.util.split_comma_delimited_string(xform.symmetryPlane, float)
    point = sirepo.util.split_comma_delimited_string(xform.symmetryPoint, float)
    if xform.symmetryType == 'parallel':
        radia.TrfZerPara(g_id, point, plane)
    if xform.symmetryType == 'perpendicular':
        radia.TrfZerPerp(g_id, point, plane)


def _apply_translation(g_id, xform):
    xform = PKDict(xform)
    radia.TrfOrnt(
        g_id,
        radia.TrfTrsl(sirepo.util.split_comma_delimited_string(xform.distance, float))
    )


def _geom_bnds(g_id):
    bnds = radia.ObjGeoLim(g_id)
    return PKDict(
        center=[0.5 * (bnds[i + 1] + bnds[i]) for i in range(3)],
        size=[abs(bnds[i + 1] - bnds[i]) for i in range(3)],
    )


def _radia_material(material_type, magnetization_dir, h_m_curve):
    if material_type == 'custom':
        return radia.MatSatIsoTab(
            [[_MU_0 * h_m_curve[i][0], h_m_curve[i][1]] for i in range(len(h_m_curve))]
        )
    return radia.MatStd(material_type, magnetization_dir)


_TRANSFORMS = PKDict(
    cloneTransform=_apply_clone,
    symmetryTransform=_apply_symmetry,
    rotate=_apply_rotation,
    translate=_apply_translation
)


def apply_color(g_id, color):
    radia.ObjDrwAtr(g_id, color)


def apply_transform(g_id, xform):
    _TRANSFORMS[xform['model']](g_id, xform)


def build_box(center, size, material, magnetization, div, h_m_curve=None):
    n_mag = numpy.linalg.norm(magnetization)
    g_id = radia.ObjRecMag(center, size, magnetization)
    if div:
        radia.ObjDivMag(g_id, div)
    if material == 'custom':
        mat = radia.MatSatIsoTab(
            [[_MU_0 * h_m_curve[i][0], h_m_curve[i][1]] for i in range(len(h_m_curve))]
        )
    else:
        mat = radia.MatStd(material, n_mag)
    radia.MatApl(g_id, mat)
    return g_id


def build_container(g_ids):
    return radia.ObjCnt(g_ids)


def build_undulator(
    num_periods, period_length,
    pole_size, pole_division, pole_material,
    magnet_cross, magnet_division, magnet_material,
    gap, gap_offset,
):

    # number of full magnetic periods
    n_periods = 2

    # period (mm)
    period = 46

    # gap height (mm)
    gap = 20
    offset = 1

    # parameters for the iron poles
    # dimensions (mm)
    lp = [45, 5, 25]

    # pole-tip segmentation
    nsp = [2, 2, 5]
    #cp = [1, 0, 0]
    ll = period / 2 - lp[1]

    # parameters for the magnet blocks
    # dimensions (mm)
    lm = [65, ll, 45]

    # magnet-block segmentation
    nsm = [1 ,3, 1]
    cm = [0, 1, 1]    # assign color

    def undulator(
            pole_lengths, pole_props, pole_segs, block_lengths, block_props,
            block_segs, gap_height, gap_offset, num_periods
    ):
        """
        create hybrid undulator magnet
        arguments:
          pole_lengths = [lpx, lpy, lpz] = dimensions of the iron poles (mm)
          pole_props = magnetic properties of the iron poles (M-H curve)
          pole_segs = segmentation of the iron poles
          block_lengths = [lmx, lmy, lmz] = dimensions of the magnet blocks (mm)
          block_props = magnetic properties of the magnet blocks (remanent magnetization)
          block_segs = segmentation of the magnet blocks
          gap_height = undulator gap (mm)
          gap_offset = vertical offset of the magnet blocks w/rt the poles (mm)
          numPer = number of full periods of the undulator magnetic field
        return: Radia representations of
          undulator group, poles, permanent magnets
        """
        zero = [0, 0, 0]

        # colors
        c_pole = [1, 0, 1]
        c_block = [0, 1, 1]

        # full magnet will be assembled into this Radia group
        grp = radia.ObjCnt([])

        # principal poles and magnet blocks in octant(+,+,–)
        # -- half pole
        y = pole_lengths[1] / 4
        pole = radia.ObjFullMag(
            [pole_lengths[0] / 4, y, -pole_lengths[2] / 2 - gap_height / 2],
            [pole_lengths[0] / 2, pole_lengths[1] / 2, pole_lengths[2]],
            zero, pole_segs, grp, pole_props, c_pole
        )
        y += pole_lengths[1] / 4

        # -- magnet and pole pairs
        m_dir = -1
        for i in range(num_periods):
            init_m = [0, m_dir, 0]
            m_dir *= -1
            y += block_lengths[1] / 2
            magnet = radia.ObjFullMag(
                [
                    block_lengths[0] / 4,
                    y,
                    -block_lengths[2] / 2 - gap_height / 2 - gap_offset
                ],
                [
                    block_lengths[0] / 2, block_lengths[1], block_lengths[2]
                ],
                init_m, block_segs, grp, block_props, c_block
            )
            y += (block_lengths[1] + pole_lengths[1]) / 2
            pole = radia.ObjFullMag(
                [pole_lengths[0] / 4, y, -pole_lengths[2] / 2 - gap_height / 2],
                [pole_lengths[0] / 2, pole_lengths[1], pole_lengths[2]],
                zero, pole_segs, grp, pole_props, c_pole
            )
            y += pole_lengths[1] / 2

        # -- end magnet block
        init_m = [0, m_dir, 0]
        y += block_lengths[1] / 4
        magnet = radia.ObjFullMag(
            [
                block_lengths[0] / 4,
                y,
                -block_lengths[2] / 2 - gap_height / 2 - gap_offset
            ],
            [
                block_lengths[0] / 2, block_lengths[1] / 2, block_lengths[2]
            ],
            init_m, block_segs, grp, block_props, c_block)

        # use mirror symmetry to define the full undulator
        radia.TrfZerPerp(grp, zero, [1, 0, 0])  # reflect in the (y,z) plane
        radia.TrfZerPara(grp, zero, [0, 0, 1])  # reflect in the (x,y) plane
        radia.TrfZerPerp(grp, zero, [0, 1, 0])  # reflect in the (z,x) plane

        return grp, pole, magnet

    def materials(h, m, smat, rm):
        """
        define magnetic materials for the undulator poles and magnets
        arguments:
          H    = list of magnetic field values / (Amp/m)
          M    = corresponding magnetization values / T
          smat = material type string
          rm   = remanent magnetization / T
        return: Radia representations of ...
          pole-tip material, magnet material
        """
        # -- magnetic property of poles
        ma = [[mu0 * h[i], m[i]] for i in range(len(h))]
        mp = radia.MatSatIsoTab(ma)
        # -- permanent magnet material
        mm = radia.MatStd(smat, rm)

        return mp, mm

    # -- magnetic materials
    # pole tips: ~iron type Va Permendur
    # permanent magnets: NdFeB with 1.2 Tesla remanent magnetization
    mp, mm = materials(iron_h, iron_m, 'NdFeB', 1.2)

    # then build the undulator
    und, pl, mg = undulator(lp, mp, nsp, lm, mm, nsm, gap, offset, n_periods)

    return und

def dump(g_id):
    return radia.UtiDmp(g_id, 'asc')


def dump_bin(g_id):
    return radia.UtiDmp(g_id, 'bin')


# only i (?), m, h
def field_integral(g_id, f_type, p1, p2):
    return radia.FldInt(g_id, 'inf', f_type, p1, p2)


def geom_to_data(g_id, name=None, divide=True):

    def _to_pkdict(d):
        if not isinstance(d, dict) or isinstance(d, PKDict):
            return d
        rv = PKDict()
        for k, v in d.items():
            rv[k] = _to_pkdict(v)
        return rv

    n = (name if name is not None else str(g_id)) + '.Geom'
    pd = PKDict(name=n, id=g_id, data=[])
    d = _to_pkdict(radia.ObjDrwVTK(g_id, 'Axes->No'))
    d.update(_geom_bnds(g_id))
    n_verts = len(d.polygons.vertices)
    c = radia.ObjCntStuf(g_id)
    l = len(c)
    if not divide or l == 0:
        pd.data = [d]
    else:
        d_arr = []
        n_s_verts = 0
        # for g in get_geom_tree(g_id):
        for g in c:
            # for fully recursive array
            # for g in get_all_geom(geom):
            s_d = _to_pkdict(radia.ObjDrwVTK(g, 'Axes->No'))
            s_d.update(_geom_bnds(g))
            n_s_verts += len(s_d.polygons.vertices)
            s_d.id = g
            d_arr.append(s_d)
        # if the number of vertices of the container is more than the total
        # across its elements, a symmetry or other "additive" transformation has
        # been applied and we cannot get at the individual elements
        if n_verts > n_s_verts:
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


# path is *flattened* array of positions in space ([x1, y1, z1,...xn, yn, zn])
def get_field(g_id, f_type, path):
    if len(path) == 0:
        return []
    pv_arr = []
    p = numpy.reshape(path, (-1, 3)).tolist()
    b = []
    # get every component
    f = radia.Fld(g_id, f_type, path)
    b.extend(f)
    b = numpy.reshape(b, (-1, 3)).tolist()
    for p_idx, pt in enumerate(p):
        pv_arr.append([pt, b[p_idx]])
    return pv_arr


def get_magnetization(g_id):
    return radia.ObjM(g_id)


def kick_map(
        g_id, begin, dir_long, num_periods, period_length, dir_trans, range_trans_1,
        num_pts_trans_1, range_trans_2, num_pts_trans_2
    ):
    return radia.FldFocKickPer(
        g_id, begin, dir_long, period_length, num_periods, dir_trans, range_trans_1,
        num_pts_trans_1, range_trans_2, num_pts_trans_2
    )


def load_bin(data):
    return radia.UtiDmpPrs(data)


def new_geom_object():
    return PKDict(
        lines=PKDict(colors=[], lengths=[], vertices=[]),
        polygons=PKDict(colors=[], lengths=[], vertices=[]),
        vectors=PKDict(directions=[], magnitudes=[], vertices=[]),
    )


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
    v_data.vectors.lengths = []
    v_data.vectors.colors = []
    v_max = 0.
    v_min = sys.float_info.max
    for i in range(len(pv_arr)):
        p = pv_arr[i][0]
        v = pv_arr[i][1]
        n = numpy.linalg.norm(v)
        v_max = max(v_max, n)
        v_min = min(v_min, n)
        nv = (numpy.array(v) / (n if n > 0 else 1.)).tolist()
        v_data.vectors.vertices.extend(p)
        v_data.vectors.directions.extend(nv)
        v_data.vectors.magnitudes.append(n)
    v_data.vectors.range = [v_min, v_max]
    v_data.vectors.units = units

    return PKDict(
        name=name + '.Field',
        id=g_id, data=[v_data],
        bounds=radia.ObjGeoLim(g_id)
    )
