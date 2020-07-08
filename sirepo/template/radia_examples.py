# -*- coding: utf-8 -*-
u"""Radia examples.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import division

import math
import radia

from sirepo.template import radia_tk

_EXAMPLES = ['Dipole', 'Wiggler', 'Undulator']

# eventually all these steps will come from the model and this will go away
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
        return t

    # Define full magnet
    return geom(1)


def undulator_example():
    mu0 = 4 * math.pi / 1e7

    # set parameters for this undulator
    # -- general parameters

    # number of full magnetic periods
    n_periods = 1  #2

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

        # full magnet will be assembled into this Radia group
        grp = radia.ObjCnt([])

        # principal poles and magnet blocks in octant(+,+,–)
        # -- half pole
        y = pole_lengths[1] / 4
        pole = radia.ObjFullMag(
            [pole_lengths[0] / 4, y, -pole_lengths[2] / 2 - gap_height / 2],
            [pole_lengths[0] / 2, pole_lengths[1] / 2, pole_lengths[2]],
            zero, pole_segs, grp, pole_props, zero
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
                init_m, block_segs, grp, block_props, zero
            )
            y += (block_lengths[1] + pole_lengths[1]) / 2
            pole = radia.ObjFullMag(
                [pole_lengths[0] / 4, y, -pole_lengths[2] / 2 - gap_height / 2],
                [pole_lengths[0] / 2, pole_lengths[1], pole_lengths[2]],
                zero, pole_segs, grp, pole_props, zero
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
            init_m, block_segs, grp, block_props, zero)

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

    return geom


def build(name):
    if name not in _EXAMPLES:
        raise KeyError('{}: No such example'.format(name))
    if name == 'Dipole':
        return dipole_example()
    if name == 'Wiggler':
        return wiggler_example()
    if name == 'Undulator':
        return undulator_example()

