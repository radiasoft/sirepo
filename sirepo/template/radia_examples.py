# -*- coding: utf-8 -*-
u"""Radia examples.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import math
import radia


def dipole_example():

    # Geometry Parameters
    gap = 10  # (mm)
    thick = 50
    width = 40
    chamfer = 8  # (mm)
    current = -2000  # (A)

    # Segmentation Parameters
    nx = 2
    nbp = 2
    nbr = 2  # for corners
    n1 = [nx, 3, 2]  # pole faces
    n2 = [nx, 2, 2]  # small vertical arm
    n3 = [nx, 2, 2]
    n4 = [nx, 2, 2]  # horizontal arm
    n5 = [nx, 2, 2]
    n6 = [nx, 2, 2]  # inside the coil

    def geom(circ):

        eps = 0
        ironcolor = [0, 0.5, 1]
        coilcolor = [1, 0, 0]
        ironmat = radia.MatSatIsoFrm([20000, 2], [0.1, 2], [0.1, 2])

        # Pole faces
        lx1 = thick / 2
        ly1 = width
        lz1 = 20
        l1 = [lx1, ly1, lz1]

        k1 = [[thick / 4. - chamfer / 2., 0, gap / 2.],
              [thick / 2. - chamfer, ly1 - 2. * chamfer]]
        k2 = [[thick / 4., 0., gap / 2. + chamfer], [thick / 2., ly1]]
        k3 = [[thick / 4., 0., gap / 2. + lz1], [thick / 2, ly1]]
        g1 = radia.ObjMltExtRtg([k1, k2, k3])
        radia.ObjDivMag(g1, n1)
        radia.ObjDrwAtr(g1, ironcolor)

        # Vertical segment on top of pole faces
        lx2 = thick / 2
        ly2 = ly1
        lz2 = 30
        l2 = [lx2, ly2, lz2]
        p2 = [thick / 4, 0, lz1 + gap / 2 + lz2 / 2 + 1 * eps]
        g2 = radia.ObjRecMag(p2, l2)
        radia.ObjDivMag(g2, n2)
        radia.ObjDrwAtr(g2, ironcolor)

        # Corner
        lx3 = thick / 2
        ly3 = ly2
        lz3 = ly2 * 1.25
        l3 = [lx3, ly3, lz3]
        p3 = [thick / 4, 0, lz1 + gap / 2 + lz2 + lz3 / 2 + 2 * eps]
        g3 = radia.ObjRecMag(p3, l3)

        typ = [
            [p3[0], p3[1] + ly3 / 2, p3[2] - lz3 / 2],
            [1, 0, 0],
            [p3[0], p3[1] - ly3 / 2, p3[2] - lz3 / 2],
            lz3 / ly3
        ]

        if circ == 1:
            radia.ObjDivMag(g3, [nbr, nbp, n3[1]], 'cyl', typ)
        else:
            radia.ObjDivMag(g3, n3)
        radia.ObjDrwAtr(g3, ironcolor)

        # Horizontal segment between the corners
        lx4 = thick / 2
        ly4 = 80
        lz4 = lz3
        l4 = [lx4, ly4, lz4]
        p4 = [thick / 4, ly3 / 2 + eps + ly4 / 2, p3[2]]
        g4 = radia.ObjRecMag(p4, l4)
        radia.ObjDivMag(g4, n4)
        radia.ObjDrwAtr(g4, ironcolor)

        # The other corner
        lx5 = thick / 2
        ly5 = lz4 * 1.25
        lz5 = lz4
        l5 = [lx5, ly5, lz5]
        p5 = [thick / 4, p4[1] + eps + (ly4 + ly5) / 2, p4[2]]
        g5 = radia.ObjRecMag(p5, l5)

        typ = [
            [p5[0], p5[1] - ly5 / 2, p5[2] - lz5 / 2],
            [1, 0, 0],
            [p5[0], p5[1] + ly5 / 2, p5[2] - lz5 / 2],
            lz5 / ly5
        ]

        if circ == 1:
            radia.ObjDivMag(g5, [nbr, nbp, n5[0]], 'cyl', typ)
        else:
            radia.ObjDivMag(g5, n5)
        radia.ObjDrwAtr(g5, ironcolor)

        # Vertical segment inside the coil
        lx6 = thick / 2
        ly6 = ly5
        lz6 = gap / 2 + lz1 + lz2
        l6 = [lx6, ly6, lz6]
        p6 = [thick / 4, p5[1], p5[2] - (lz6 + lz5) / 2 - eps]
        g6 = radia.ObjRecMag(p6, l6)
        radia.ObjDivMag(g6, n6)
        radia.ObjDrwAtr(g6, ironcolor)

        # Generation of the coil
        r_min = 5
        r_max = 40
        h = 2 * lz6 - 5

        cur_dens = current / h / (r_max - r_min)
        pc = [0, p6[1], 0]
        coil = radia.ObjRaceTrk(pc, [r_min, r_max], [thick, ly6], h, 3, cur_dens)
        radia.ObjDrwAtr(coil, coilcolor)

        # Make container and set the colors
        g = radia.ObjCnt([g1, g2, g3, g4, g5, g6])
        radia.ObjDrwAtr(g, ironcolor)
        radia.MatApl(g, ironmat)
        t = radia.ObjCnt([g, coil])

        # Define the symmetries
        radia.TrfZerPerp(g, [0, 0, 0], [1, 0, 0])
        radia.TrfZerPara(g, [0, 0, 0], [0, 0, 1])
        return t, {
            g: '1c3a32be-c19b-42f8-a303-28fecaa5c1f0',
            coil: 'f904f1d1-93d5-4a84-bafb-cebf9efa0b35',
        }

    # Define full magnet
    return geom(1)


def sagu_example():
    import math
    def HybridUnd(_gap, _gap_ofst, _nper, _air, _lp, _ed_p, _ch_p, _np, _np_tip, _mp, _cp,
                  _lm, _ch_m_xz, _ch_m_yz, _ch_m_yz_r, _nm, _mm, _cm, _tm=None,
                  _use_ex_sym=False):

        zer = [0, 0, 0]
        grp = radia.ObjCnt([])

        y = _lp[1] / 4
        my0 = (-1.) ** (_nper - 1)
        initM = [0, my0, 0]  # [0,-1,0]

        poleEarsDef = False
        if (_ed_p is not None):
            if (isinstance(_ed_p, list)):
                if ((_ed_p[0] > 0.) and (_ed_p[1] > 0.)): poleEarsDef = True

        halfNpy = int(_np[1] / 2 + 0.5)
        pole = radia.ObjFullMag([_lp[0] / 4, y, -_lp[2] / 2 - _gap / 2 - _ch_p],
                              [_lp[0] / 2, _lp[1] / 2, _lp[2]], zer,
                              [_np[0], halfNpy, _np[2]], grp, _mp, _cp)

        if (poleEarsDef): radia.ObjFullMag(
            [_lp[0] / 2 + _ed_p[0] / 2, y, -_lp[2] - _gap / 2 - _ch_p + _ed_p[1] / 2],
            [_ed_p[0], _lp[1] / 2, _ed_p[1]], zer, [1, halfNpy, 1], grp, _mp, _cp)

        if (_ch_p > 0.):  # Pole Tip
            poleTip = radia.ObjThckPgn(_lp[0] / 4, _lp[0] / 2,
                                     [[y - _lp[1] / 4, -_gap / 2 - _ch_p],
                                      [y - _lp[1] / 4, -_gap / 2],
                                      [y + _lp[1] / 4 - _ch_p, -_gap / 2],
                                      [y + _lp[1] / 4, -_gap / 2 - _ch_p]], zer)
            radia.ObjDivMag(poleTip, [_np_tip[0], int(_np_tip[1] / 2 + 0.5), _np_tip[2]])
            radia.MatApl(poleTip, mp)
            radia.ObjDrwAtr(poleTip, _cp)
            radia.ObjAddToCnt(grp, [poleTip])

        y += _lp[1] / 4 + _air + _lm[1] / 2

        for i in range(_nper):
            magnet = radia.ObjThckPgn(_lm[0] / 4, _lm[0] / 2,
                                    [[y + _lm[1] / 2 - _ch_m_yz_r * _ch_m_yz,
                                      -_gap / 2 - _gap_ofst],
                                     [y + _lm[1] / 2, -_gap / 2 - _gap_ofst - _ch_m_yz],
                                     [y + _lm[1] / 2,
                                      -_gap / 2 - _gap_ofst - _lm[2] + _ch_m_yz],
                                     [y + _lm[1] / 2 - _ch_m_yz_r * _ch_m_yz,
                                      -_gap / 2 - _gap_ofst - _lm[2]],
                                     [y - _lm[1] / 2 + _ch_m_yz_r * _ch_m_yz,
                                      -_gap / 2 - _gap_ofst - _lm[2]],
                                     [y - _lm[1] / 2,
                                      -_gap / 2 - _gap_ofst - _lm[2] + _ch_m_yz],
                                     [y - _lm[1] / 2, -_gap / 2 - _gap_ofst - _ch_m_yz],
                                     [y - _lm[1] / 2 + _ch_m_yz_r * _ch_m_yz,
                                      -_gap / 2 - _gap_ofst]], initM)
            # Cuting Magnet Corners
            magnet = \
            radia.ObjCutMag(magnet, [_lm[0] / 2 - _ch_m_xz, 0, -_gap / 2 - _gap_ofst],
                          [1, 0, 1])[0]
            magnet = radia.ObjCutMag(magnet, [_lm[0] / 2 - _ch_m_xz, 0,
                                            -_gap / 2 - _gap_ofst - _lm[2]], [1, 0, -1])[
                0]
            radia.ObjDivMag(magnet, _nm)
            radia.MatApl(magnet, _mm)
            radia.ObjDrwAtr(magnet, _cm)
            radia.ObjAddToCnt(grp, [magnet])
            initM[1] *= -1

            y += _lm[1] / 2 + _lp[1] / 2 + _air

            if (i < _nper - 1):
                pole = radia.ObjFullMag([_lp[0] / 4, y, -_lp[2] / 2 - _gap / 2 - _ch_p],
                                      [_lp[0] / 2, _lp[1], _lp[2]], zer, _np, grp, _mp,
                                      _cp)

                if (poleEarsDef): radia.ObjFullMag([_lp[0] / 2 + _ed_p[0] / 2, y,
                                                  -_lp[2] - _gap / 2 - _ch_p + _ed_p[
                                                      1] / 2],
                                                 [_ed_p[0], _lp[1], _ed_p[1]], zer,
                                                 [1, _np[1], 1], grp, _mp, _cp)

                if (_ch_p > 0.):  # Pole Tip
                    poleTip = radia.ObjThckPgn(_lp[0] / 4, _lp[0] / 2,
                                             [[y - _lp[1] / 2, -_gap / 2 - _ch_p],
                                              [y - _lp[1] / 2 + _ch_p, -_gap / 2],
                                              [y + _lp[1] / 2 - _ch_p, -_gap / 2],
                                              [y + _lp[1] / 2, -_gap / 2 - _ch_p]], zer)
                    radia.ObjDivMag(poleTip, _np_tip)
                    radia.MatApl(poleTip, mp)
                    radia.ObjDrwAtr(poleTip, _cp)
                    radia.ObjAddToCnt(grp, [poleTip])

                y += _lm[1] / 2 + _lp[1] / 2 + _air

        npyNextPole = _np[1]
        thickNextPole = _lp[1]
        if (_use_ex_sym):
            y -= _lp[1] / 4
            thickNextPole = _lp[1] / 2
            npyNextPole = halfNpy

        pole = radia.ObjFullMag([_lp[0] / 4, y, -_lp[2] / 2 - _gap / 2 - _ch_p],
                              [_lp[0] / 2, thickNextPole, _lp[2]], zer,
                              [_np[0], npyNextPole, _np[2]], grp, _mp, _cp)

        if (poleEarsDef): radia.ObjFullMag(
            [_lp[0] / 2 + _ed_p[0] / 2, y, -_lp[2] - _gap / 2 - _ch_p + _ed_p[1] / 2],
            [_ed_p[0], thickNextPole, _ed_p[1]], zer, [1, npyNextPole, 1], grp, _mp, _cp)

        if (_ch_p > 0.):  # Pole Tip
            if (_use_ex_sym):
                poleTip = radia.ObjThckPgn(_lp[0] / 4, _lp[0] / 2,
                                         [[y - _lp[1] / 4, -_gap / 2 - _ch_p],
                                          [y - _lp[1] / 4 + _ch_p, -_gap / 2],
                                          [y + _lp[1] / 4, -_gap / 2],
                                          [y + _lp[1] / 4, -_gap / 2 - _ch_p]], zer)
            else:
                poleTip = radia.ObjThckPgn(_lp[0] / 4, _lp[0] / 2,
                                         [[y - _lp[1] / 2, -_gap / 2 - _ch_p],
                                          [y - _lp[1] / 2 + _ch_p, -_gap / 2],
                                          [y + _lp[1] / 2 - _ch_p, -_gap / 2],
                                          [y + _lp[1] / 2, -_gap / 2 - _ch_p]], zer)

            radia.ObjDivMag(poleTip, [_np_tip[0], npyNextPole, _np_tip[2]])
            radia.MatApl(poleTip, mp)
            radia.ObjDrwAtr(poleTip, _cp)
            radia.ObjAddToCnt(grp, [poleTip])

        if (_tm is not None):
            if (isinstance(_tm, list)):
                colCoef = 0.5
                cmt = [_cm[0] * colCoef, _cm[1] * colCoef,
                       _cm[2] * colCoef]  # Termination Magnet Color
                cpt = [_cp[0] * colCoef, _cp[1] * colCoef,
                       _cp[2] * colCoef]  # Termination Pole Color

                # First (thick) Magnet of Termination, located next to the central part of the structure
                htm0 = _tm[0] / 2
                y += _lp[1] / 2 + _air + htm0
                magnet = radia.ObjThckPgn(_lm[0] / 4, _lm[0] / 2,
                                        [[y + htm0 - _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst],
                                         [y + htm0, -_gap / 2 - _gap_ofst - _ch_m_yz],
                                         [y + htm0,
                                          -_gap / 2 - _gap_ofst - _lm[2] + _ch_m_yz],
                                         [y + htm0 - _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst - _lm[2]],
                                         [y - htm0 + _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst - _lm[2]],
                                         [y - htm0,
                                          -_gap / 2 - _gap_ofst - _lm[2] + _ch_m_yz],
                                         [y - htm0, -_gap / 2 - _gap_ofst - _ch_m_yz],
                                         [y - htm0 + _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst]], initM)
                # Cuting Magnet Corners
                magnet = \
                radia.ObjCutMag(magnet, [_lm[0] / 2 - _ch_m_xz, 0, -_gap / 2 - _gap_ofst],
                              [1, 0, 1])[0]
                magnet = radia.ObjCutMag(magnet, [_lm[0] / 2 - _ch_m_xz, 0,
                                                -_gap / 2 - _gap_ofst - _lm[2]],
                                       [1, 0, -1])[0]
                radia.ObjDivMag(magnet, _nm)
                radia.MatApl(magnet, _mm)
                radia.ObjDrwAtr(magnet, cmt)
                radia.ObjAddToCnt(grp, [magnet])
                initM[1] *= -1

                # Pole of Terminaiton
                htm2 = _tm[2] / 2
                y += htm0 + _tm[1] + htm2
                pole = radia.ObjFullMag([_lp[0] / 4, y, -_lp[2] / 2 - _gap / 2 - _ch_p],
                                      [_lp[0] / 2, _tm[2], _lp[2]], zer, _np, grp, _mp,
                                      cpt)
                if (poleEarsDef): radia.ObjFullMag([_lp[0] / 2 + _ed_p[0] / 2, y,
                                                  -_lp[2] - _gap / 2 - _ch_p + _ed_p[
                                                      1] / 2],
                                                 [_ed_p[0], _tm[2], _ed_p[1]], zer,
                                                 [1, _np[1], 1], grp, _mp, cpt)
                if (_ch_p > 0.):  # Pole Tip
                    poleTip = radia.ObjThckPgn(_lp[0] / 4, _lp[0] / 2,
                                             [[y - htm2, -_gap / 2 - _ch_p],
                                              [y - htm2 + _ch_p, -_gap / 2],
                                              [y + htm2 - _ch_p, -_gap / 2],
                                              [y + htm2, -_gap / 2 - _ch_p]], zer)
                    radia.ObjDivMag(poleTip, _np_tip)
                    radia.MatApl(poleTip, mp)
                    radia.ObjDrwAtr(poleTip, cpt)
                    radia.ObjAddToCnt(grp, [poleTip])

                # First (thin) Magnet of Termination, located at the extremity of the structure
                htm4 = _tm[4] / 2
                y += htm2 + _tm[3] + htm4
                magnet = radia.ObjThckPgn(_lm[0] / 4, _lm[0] / 2,
                                        [[y + htm4 - _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst],
                                         [y + htm4, -_gap / 2 - _gap_ofst - _ch_m_yz],
                                         [y + htm4,
                                          -_gap / 2 - _gap_ofst - _lm[2] + _ch_m_yz],
                                         [y + htm4 - _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst - _lm[2]],
                                         [y - htm4 + _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst - _lm[2]],
                                         [y - htm4,
                                          -_gap / 2 - _gap_ofst - _lm[2] + _ch_m_yz],
                                         [y - htm4, -_gap / 2 - _gap_ofst - _ch_m_yz],
                                         [y - htm4 + _ch_m_yz_r * _ch_m_yz,
                                          -_gap / 2 - _gap_ofst]], initM)
                # Cuting Magnet Corners
                magnet = \
                radia.ObjCutMag(magnet, [_lm[0] / 2 - _ch_m_xz, 0, -_gap / 2 - _gap_ofst],
                              [1, 0, 1])[0]
                magnet = radia.ObjCutMag(magnet, [_lm[0] / 2 - _ch_m_xz, 0,
                                                -_gap / 2 - _gap_ofst - _lm[2]],
                                       [1, 0, -1])[0]
                radia.ObjDivMag(magnet, _nm)
                radia.MatApl(magnet, _mm)
                radia.ObjDrwAtr(magnet, cmt)
                radia.ObjAddToCnt(grp, [magnet])

        # Symmetries
        if (
        _use_ex_sym):  # Some "non-physical" mirroring (applicable for calculation of central field only)
            y += _lp[1] / 4
            radia.TrfZerPerp(grp, [0, y, 0], [0, 1, 0])  # Mirror left-right
            radia.TrfZerPerp(grp, [0, 2 * y, 0], [0, 1, 0])

        # "Physical" symmetries (applicable also for calculation of total structure with terminations)
        radia.TrfZerPerp(grp, zer, [0, 1, 0])  # Mirror left-right
        # Mirror front-back
        radia.TrfZerPerp(grp, zer, [1, 0, 0])
        # Mirror top-bottom
        radia.TrfZerPara(grp, zer, [0, 0, 1])

        return grp

    per = 20.18
    nPer = 4

    gap = 3.5
    gapOffset = 0.
    air = 0.05

    poleThick = 2.8

    poleHeight = 19.5
    poleWidth = 42.
    lp = [poleWidth, poleThick, poleHeight]

    poleCh = 0.1  # If cham_pole > 0, it adds pole tip
    poleEarDim = [3., 3.]  # Horizontal and Vertical sizes of Pole Ears for clamping

    npx = 12
    npy = 6

    np = [npx, npy, [15, 0.18]]  # Pole Subdivision Params

    npTip = [npx, npy, 1]  # Pole Tip Subdivision Params
    cp = [1., 0., 1.]  # Pole Color

    magThick = per / 2 - poleThick - 2 * air

    magHeight = 27.
    magWidth = 58.
    lm = [magWidth, magThick, magHeight]

    nm = [3, 2, [6, 1. / 3.]]  # Magnet Subdivision Params

    cm = [0., 1., 1.]  # Magnet Color

    chMagXZ = 5.  # Magnet Chamfer in the XZ plane
    chMagYZ = 0.05  # Magnet Chamfer in the YZ plane
    chMagYZrat = math.sqrt(3.)  # Magnet Chamfer Ratio: Longitudinal/Vertical

    termThick = [5.2, 3.0, 1.4, 0.9,
                 2.3]  # Thicknesses (longitudinal sizes) of Termination: Thick Magnet, Space 1, Pole, Space 2, Thin Magnet 

    # Pole Material 
    # B [G] vs H [G] data from NEOMAX
    BvsH_G = [[0., 0], [0.5, 5000], [1, 10000], [1.5, 13000], [2, 15000], [3, 16500],
              [4, 17400], [6, 18500], [8, 19250], [10, 19800],
              [12, 20250], [14, 20600], [16, 20900], [18, 21120], [20, 21250],
              [25, 21450], [30, 21590], [40, 21850], [50, 22000],
              [70, 22170], [100, 22300], [200, 22500], [300, 22650], [500, 23000],
              [1000, 23900], [2000, 24900]]
    MvsH_T = [[BvsH_G[i][0] * 1.e-04, (BvsH_G[i][1] - BvsH_G[i][0]) * 1.e-04] for i in
              range(len(BvsH_G))]

    mp = radia.MatStd('AFK502')

    # Magnet Material
    magBr = 1.19  # Remanent Magnetization
    mm = radia.MatLin({0.05, 0.15}, magBr)

    geom = HybridUnd(_gap=gap, _gap_ofst=gapOffset, _nper=nPer, _air=air,
                    _lp=lp, _ed_p=poleEarDim, _ch_p=poleCh, _np=np, _np_tip=npTip, _mp=mp,
                    _cp=cp,
                    _lm=lm, _ch_m_xz=chMagXZ, _ch_m_yz=chMagYZ, _ch_m_yz_r=chMagYZrat,
                    _nm=nm, _mm=mm, _cm=cm, _tm=termThick)

    return geom, {
        geom: 'c4649553-fd32-4456-85b3-8a40f28d53ff',
    }

# DEPRECATED
def undulator_example():
    mu0 = 4 * math.pi / 1e7

    # set parameters for this undulator
    # -- general parameters

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

    # ~iron type Va Permendur
    iron_h = [
        0.8, 1.5, 2.2, 3.6, 5.0, 6.8, 9.8, 18.0,
        28.0, 37.5, 42.0, 55.0, 71.5, 80.0, 85.0, 88.0,
        92.0, 100.0, 120.0, 150.0, 200.0, 300.0, 400.0, 600.0,
        800.0, 1000.0, 2000.0, 4000.0, 6000.0, 10000.0, 25000.0, 40000.0
    ]
    iron_m = [
        0.000998995, 0.00199812, 0.00299724, 0.00499548, 0.00699372, 0.00999145,
        0.0149877, 0.0299774, 0.0499648, 0.0799529, 0.0999472, 0.199931, 0.49991,
        0.799899, 0.999893, 1.09989, 1.19988, 1.29987, 1.41985, 1.49981, 1.59975,
        1.72962, 1.7995, 1.89925, 1.96899, 1.99874, 2.09749, 2.19497, 2.24246, 2.27743,
        2.28958,  2.28973
    ]

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
        c_pole = [1, 0, 0]
        c_block = [0, 0, 1]

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


def wiggler_example():
    # current densities in A / mm^2
    j1 = 128
    j2 = 256

    # number of arc segments
    n1 = 3
    n2 = 6

    # create 5 racetrack coils above the mid-plane:
    #   lower inside, lower outside, upper inside, upper outside, and circular
    # radia.ObjRaceTrk[ctr:[x,y,z], rad:[r1,r2], lstr:[lx,ly], ht, nseg, j]
    rt1 = radia.ObjRaceTrk([0., 0., 38.], [9.5, 24.5], [120., 0.], 36, n1, j1)
    rt2 = radia.ObjRaceTrk([0., 0., 38.], [24.5, 55.5], [120., 0.], 36, n1, j2)
    rt3 = radia.ObjRaceTrk([0., 0., 76.], [10.0, 25.0], [90., 0.], 24, n1, j1)
    rt4 = radia.ObjRaceTrk([0., 0., 76.], [25.0, 55.0], [90., 0.], 24, n1, j2)
    rt5 = radia.ObjRaceTrk([0., 0., 60.], [150.0, 166.3], [0., 0.], 39, n2, -j2)

    c1 = [0.0,1.0,1.0] # blue/green
    c2 = [1.0,0.4,0.0] # orange-red
    thcn = 0.001
    radia.ObjDrwAtr(rt1, c1, thcn)
    radia.ObjDrwAtr(rt2, c2, thcn)
    radia.ObjDrwAtr(rt3, c1, thcn)
    radia.ObjDrwAtr(rt4, c2, thcn)
    radia.ObjDrwAtr(rt5, c2, thcn)

    # assemble into a group
    geom = radia.ObjCnt([rt1, rt2, rt3, rt4, rt5])

    # and reflect in the (x,y) plane [plane through (0,0,0) with normal (0,0,1)]
    radia.TrfZerPara(geom, [0, 0, 0], [0, 0, 1])

    return geom, {
        geom: '48022af9-3b43-424f-b43b-5cbeb0d36bd6',
    }


EXAMPLES = {
    'Dipole': dipole_example,
    'SAGU': sagu_example,
    'Wiggler': wiggler_example,
}

