# -*- coding: utf-8 -*-
"""Particle beam generator and analyzer.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import numpy as np
from pykern.pkdebug import pkdp
import scipy.constants as sc

m_p_MeV = sc.physical_constants["proton mass energy equivalent in MeV"][0]
m_p_GeV = m_p_MeV / 1.0e3


def analyze_ptc_beam(ptc_beam_data, mc2=m_p_GeV):
    """
    On the basis of particle tracking data, compute Twiss functions,
    rms beam sizes, etc.
    Return results in a dictionary.
    """
    ptc_beam_summary = []

    for i in range(0, len(ptc_beam_data)):
        # each beam snapshot has the following columns
        #  ptcl# turn  X PX  Y PY  T PT  S  E
        #   0      1   2 3   4 5   6 7   8  9
        snap = ptc_beam_data[i].copy()
        n = float(len(snap))
        x0 = np.mean(snap[:, 2])
        px0 = np.mean(snap[:, 3])
        y0 = np.mean(snap[:, 4])
        py0 = np.mean(snap[:, 5])
        ct0 = np.mean(snap[:, 6])  # –c * dt / meter
        pt0 = np.mean(snap[:, 7])  # dE / p0c = dgamma / (beta gamma)_0
        s0 = np.mean(snap[:, 8])
        E0 = np.mean(snap[:, 9])
        x = snap[:, 2] - x0
        px = snap[:, 3] - px0
        y = snap[:, 4] - y0
        py = snap[:, 5] - py0
        ct = snap[:, 6] - ct0
        pt = snap[:, 7] - pt0
        gamma = E0 / mc2
        beta = np.sqrt(1.0 - 1.0 / (gamma**2))
        pz = mc2 * beta * gamma
        W = E0

        xct = np.dot(x, ct) / n
        xpt = np.dot(x, pt) / n
        pxct = np.dot(px, ct) / n
        pxpt = np.dot(px, pt) / n
        yct = np.dot(y, ct) / n
        ypt = np.dot(y, pt) / n
        pyct = np.dot(py, ct) / n
        pypt = np.dot(py, pt) / n
        ctct = np.dot(ct, ct) / n
        ctpt = np.dot(ct, pt) / n
        ptpt = np.dot(pt, pt) / n

        eta_x = xpt / ptpt
        eta_y = ypt / ptpt
        eta_px = pxpt / ptpt
        eta_py = pypt / ptpt

        # remove dispersive component of the transverse motion
        x = x - pt * eta_x
        y = y - pt * eta_y
        px = px - pt * eta_px
        py = py - pt * eta_py

        xx = np.dot(x, x) / n
        xpx = np.dot(x, px) / n
        xy = np.dot(x, y) / n
        xpy = np.dot(x, py) / n
        pxpx = np.dot(px, px) / n
        pxy = np.dot(px, y) / n
        pxpy = np.dot(px, py) / n
        yy = np.dot(y, y) / n
        ypy = np.dot(y, py) / n
        pypy = np.dot(py, py) / n

        # accumulate summary data for each beam snapshot
        ptc_beam_summary.append(
            [
                s0,
                n,
                xx,
                xpx,
                xy,
                xpy,
                xct,
                xpt,
                pxpx,
                pxy,
                pxpy,
                pxct,
                pxpt,
                yy,
                ypy,
                yct,
                ypt,
                pypy,
                pyct,
                pypt,
                ctct,
                ctpt,
                ptpt,
                W,
                x0,
                px0,
                y0,
                py0,
                ct0,
                pt0,
                eta_x,
                eta_px,
                eta_y,
                eta_py,
            ]
        )

    ptc_beam_array = np.asarray(ptc_beam_summary)

    ptc_beam_dict = {}
    keys = [
        "s",
        "n",
        "xx",
        "xpx",
        "xy",
        "xpy",
        "xct",
        "xpt",
        "pxpx",
        "pxy",
        "pxpy",
        "pxct",
        "pxpt",
        "yy",
        "ypy",
        "yct",
        "ypt",
        "pypy",
        "pyct",
        "pypt",
        "ctct",
        "ctpt",
        "ptpt",
        "W",
        "x0",
        "px0",
        "y0",
        "py0",
        "ct0",
        "pt0",
        "eta_x",
        "eta_px",
        "eta_y",
        "eta_py",
    ]

    for i in range(0, len(keys)):
        ptc_beam_dict[keys[i]] = ptc_beam_array[:, i]

    ptc_beam_dict["emit_x"] = np.sqrt(
        ptc_beam_dict["xx"] * ptc_beam_dict["pxpx"] - ptc_beam_dict["xpx"] ** 2.0
    )
    ptc_beam_dict["emit_y"] = np.sqrt(
        ptc_beam_dict["yy"] * ptc_beam_dict["pypy"] - ptc_beam_dict["ypy"] ** 2.0
    )
    ptc_beam_dict["emit_t"] = np.sqrt(
        ptc_beam_dict["ctct"] * ptc_beam_dict["ptpt"] - ptc_beam_dict["ctpt"] ** 2.0
    )

    ptc_beam_dict["beta_x"] = ptc_beam_dict["xx"] / ptc_beam_dict["emit_x"]
    ptc_beam_dict["beta_y"] = ptc_beam_dict["yy"] / ptc_beam_dict["emit_y"]

    ptc_beam_dict["alpha_x"] = -ptc_beam_dict["xpx"] / ptc_beam_dict["emit_x"]
    ptc_beam_dict["alpha_y"] = -ptc_beam_dict["ypy"] / ptc_beam_dict["emit_y"]

    ptc_beam_dict["gamma_x"] = ptc_beam_dict["pxpx"] / ptc_beam_dict["emit_x"]
    ptc_beam_dict["gamma_y"] = ptc_beam_dict["pypy"] / ptc_beam_dict["emit_y"]

    ptc_beam_dict["sx"] = np.sqrt(ptc_beam_dict["xx"])
    ptc_beam_dict["sy"] = np.sqrt(ptc_beam_dict["yy"])

    return ptc_beam_dict


def populate_uncoupled_beam(
    num_particles,
    beta_x,
    alpha_x,
    emittance_x,
    beta_y,
    alpha_y,
    emittance_y,
    dtau,
    dpt,
    iseed=None,
):
    """
    Return a particle beam matched to point described by given Twiss parameters.

    This function populates phase-space with a distribution matched to a
    given point of injection. The essential technique used here is to first
    populate each transverse phase-space plane with a disc of area π * emittance,
    which amounts to populating the beam in terms of normalized coördinates.
    We then use the normalizing matrix at the 'point of injection' to transform
    the beam from normalized coördinates to physical coördinates.
    In one degree of freedom, and in the Courant-Snyder gauge, the normalizing
    matrix has the form A = [[rt(beta), 0], [-alpha/rt(beta), 1/rt(beta)]].
    This techniques works even for coupled systems.

    If one does not set any special flags in Mad-X/PTC, then the phase-space
    variables are (X, PX, Y, PY, T, PT), where X and Y denote the transverse
    coördinates, measured in meters; PX and PY denote the transverse canonical
    momenta scaled by the reference momentum; T denotes -cΔt, measured in
    meters; and PT denotes the scaled energy deviation ΔE / p_0c.

    NB: A particle with _positive_ T arrives _ahead_ of the reference particle.

    Argumcov, alfa_x, emittance_x -- Twiss parameters and emittance in the X plane
    beta_y, alfa_y, emittance_y -- Twiss parameters and emittance in the Y plane
    dtau -- variation in T = -ct
    dpt -- variation in PT
    iseed -- initial seed for the random number generator; defaults to None,
               in which case “unpredictable entropy will be pulled from the OS”
    """
    # (pseudo)random number generator
    rng = np.random.default_rng(seed=iseed)

    # abbreviations
    n_ptcl = num_particles
    ex = emittance_x
    ey = emittance_y
    # ect    = emittance_ct

    # uncoupled, 4D normalizing matrix (in the Courant-Snyder gauge)
    # [for an uncoupled system, we can write this in terms of Twiss parameters]
    # [for a coupled system, we will need access to the full normalizing matrix]
    normalizing_A = np.asarray(
        [
            [np.sqrt(beta_x), 0, 0, 0],
            [-alpha_x / np.sqrt(beta_x), 1 / np.sqrt(beta_x), 0, 0],
            [0, 0, np.sqrt(beta_y), 0],
            [0, 0, -alpha_y / np.sqrt(beta_y), 1 / np.sqrt(beta_y)],
        ]
    )

    # transverse beam distribution
    mean = np.zeros(4)
    cov = np.identity(4)
    for i in [0, 1]:
        cov[i, i] = ex
    for i in [2, 3]:
        cov[i, i] = ey
    transverse = np.matmul(normalizing_A, rng.multivariate_normal(mean, cov, n_ptcl).T)
    x = transverse[0]
    xp = transverse[1]
    y = transverse[2]
    yp = transverse[3]

    # longitudinal distribuion
    long_dist = rng.multivariate_normal([0, 0], [[dtau**2, 0], [0, dpt**2]], n_ptcl).T
    ct = long_dist[0]
    pt = long_dist[1]

    # return the particle array
    return np.column_stack([x, xp, y, yp, -ct, pt])


def read_ptc_data(file_name):
    """
    Read PTC output data, and put the results in two arrays,
    one containing the particle data as a sequence of snapshots,
    and a second containing the names of the observation points.
    """
    f = open(file_name, "r")
    table = [line.strip().split() for line in f]

    ptc_beam_data = []
    ptc_observe_names = []
    k = 0
    while k < len(table):
        line = table[k]
        k += 1

        if "NUMBER" in line:
            ptc_column_names = line[1::]

        if "#segment" in line:
            ptc_observe_names.append(line[-1])
            n_particles = int(line[3])
            beam_snapshot = np.asarray(table[k : k + n_particles]).astype(float)
            ptc_beam_data.append(beam_snapshot)
            k += n_particles

    return ptc_beam_data, ptc_observe_names, ptc_column_names
