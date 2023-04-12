# -*- coding: utf-8 -*-
"""Radia examples.

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

        k1 = [
            [thick / 4.0 - chamfer / 2.0, 0, gap / 2.0],
            [thick / 2.0 - chamfer, ly1 - 2.0 * chamfer],
        ]
        k2 = [[thick / 4.0, 0.0, gap / 2.0 + chamfer], [thick / 2.0, ly1]]
        k3 = [[thick / 4.0, 0.0, gap / 2.0 + lz1], [thick / 2, ly1]]
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
            lz3 / ly3,
        ]

        if circ == 1:
            radia.ObjDivMag(g3, [nbr, nbp, n3[1]], "cyl", typ)
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
            lz5 / ly5,
        ]

        if circ == 1:
            radia.ObjDivMag(g5, [nbr, nbp, n5[0]], "cyl", typ)
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
            g: "1c3a32be-c19b-42f8-a303-28fecaa5c1f0",
            coil: "f904f1d1-93d5-4a84-bafb-cebf9efa0b35",
        }

    # Define full magnet
    return geom(1)


EXAMPLES = {
    "Dipole": dipole_example,
}
