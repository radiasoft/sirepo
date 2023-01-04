from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import Shadow
import numpy as np
import scipy.linalg as sla


def shadow_src_beam(
    n_rays=10000,
    ran_seed=15829,
    dist_type=3,
    sigx=4.42e-05,
    sigz=2.385e-05,
    sigdix=3.52e-05,
    sigdiz=2.875e-05,
    hdiv1=0.0,
    hdiv2=0.0,
    vdiv1=0.0,
    vdiv2=0.0,
    ph_energy=1e3,
):
    """
    This function computes a shadow
    beam object from a specified source.
    """

    source = Shadow.Source()
    beam = Shadow.Beam()

    source.NPOINT = n_rays  # no. of rays (1 on-axis ray, 4 deviations)
    source.ISTAR1 = ran_seed

    # source.FSOUR = src_type  # source type (0 = point, 3 = Gsn)
    # source.WXSOU = wx
    # source.WZSOU = wz
    source.SIGMAX = sigx
    source.SIGMAZ = sigz
    source.FDISTR = dist_type
    source.SIGDIX = sigdix
    source.SIGDIZ = sigdiz
    source.F_POLAR = 0
    source.HDIV1 = hdiv1
    source.HDIV2 = hdiv2
    source.VDIV1 = vdiv1
    source.VDIV2 = vdiv2
    source.IDO_VX = 0
    source.IDO_VZ = 0
    source.IDO_X_S = 0
    source.IDO_Y_S = 0
    source.IDO_Z_S = 0
    source.F_PHOT = 0
    source.PH1 = ph_energy
    beam.genSource(source)

    return beam


def create_mat_rays(epsilon, ph_energy):
    # Use Shadow MC generation for 5 rays from source in beam object
    beam = shadow_src_beam(n_rays=5, ph_energy=ph_energy)

    # Manually set initial phase space values for each ray (1 on-axis and 4 offset)

    # on-axis ray
    beam.rays[0, 0] = 0
    beam.rays[0, 1:4] = 0
    beam.rays[0, 5:6] = 0

    # 1st ray: x = epsilon
    beam.rays[1, 0] = epsilon
    beam.rays[1, 1:4] = 0
    beam.rays[1, 5:6] = 0

    # 2nd ray: x' = epsilon
    beam.rays[2, 3] = epsilon
    beam.rays[2, 0:3] = 0
    beam.rays[2, 5:6] = 0

    # 3rd ray: z = epsilon
    beam.rays[3, 2] = epsilon
    beam.rays[3, 0:2] = 0
    beam.rays[3, 3] = 0
    beam.rays[3, 5:6] = 0

    # 4th ray: z' = epsilon
    beam.rays[4, 5] = epsilon
    beam.rays[4, 0:4] = 0

    return beam


def create_shadow_ellip_mir(
    alpha=0.0,
    t_source=2850.0,
    t_image=0.0,
    ssour=2850.0,
    simag=900.0,
    theta=87.9998043372,
    offz=0.0,
    mirinfo=0,
):
    """
    This function returns a Shadow
    elliptical mirror optical element
    object.
    t_source: source plane distance (drift length before mirror) - assumedly in cm
    t_image: image plane distance (drift length after mirror) - assumedly in cm
    ssour: distance from source to mirror center [cm] (object side focal distance)
    simag: distance from mirror center to second focus [cm] (image side focal distance)
    theta: incidence/reflection angle [deg]
    offz: mirror offset [cm]
    mirinfo: print mirror info; 0 = off, 1 = on
    """

    oe = Shadow.OE()
    oe.DUMMY = 100.0
    oe.FMIRR = 2  # 2: ellipsoidal, 3: toroidal, 10: conic with external coefficients
    oe.ALPHA = alpha
    oe.FHIT_C = 1
    oe.F_EXT = 0  # toggle auto-compute mirror parameters
    oe.F_DEFAULT = 0
    oe.SSOUR = ssour
    oe.SIMAG = simag
    oe.THETA = theta
    oe.FCYL = 1
    oe.FSHAPE = 2
    oe.RWIDX1 = 0.05  # added from oasys # X(+) Half Width / Int Maj Ax [m]
    oe.RWIDX2 = 0.05  # changed from oasys # X(-) Half Width / Int Maj Ax [m]
    oe.RLEN1 = 0.11  # added from oasys # Y(+) Half Width / Int Min Ax [m]
    oe.RLEN2 = 0.11  # changed from oasys # Y(-) Half Width / Int Min Ax [m]
    oe.T_INCIDENCE = theta
    oe.T_REFLECTION = theta
    oe.FWRITE = 0
    oe.T_IMAGE = t_image  # Image plane distance (drift length after mirror)
    oe.T_SOURCE = t_source  # Source plane distance (drift length before mirror)
    oe.F_MOVE = 1
    oe.OFFX = 0.0
    oe.OFFZ = offz
    # oe.Y_ROT = 0
    # oe.Z_ROT = 0
    if mirinfo == 1:
        pkdlog(oe.mirinfo())

    return oe


def shadow_ellip_mir_trace(
    beam,
    oe_num=1,
    alpha=0.0,
    t_source=2850.0,
    t_image=0.0,
    ssour=2850.0,
    simag=900.0,
    theta=87.9998043372,
    offz=0.0,
    mirinfo=0,
):
    """
    This function propagates an input
    beam object through an elliptical
    mirror element.
    beam: shadow beam object
    oe_num: optical element sequence number along beamline (1, 2, 3,...)
    t_source: source plane distance (drift length before mirror) - assumedly in cm
    t_image: image plane distance (drift length after mirror) - assumedly in cm
    ssour: distance from source to mirror center [cm] (object side focal distance)
    simag: distance from mirror center to second focus [cm] (image side focal distance)
    theta: incidence/reflection angle [deg]
    offz: mirror offset [cm]
    mirinfo: print mirror info; 0 = off, 1 = on
    """

    oe = Shadow.OE()
    oe.DUMMY = 100.0
    oe.FMIRR = 2  # 2: ellipsoidal, 3: toroidal, 10: conic with external coefficients
    oe.ALPHA = alpha
    oe.FHIT_C = 1
    oe.F_EXT = 0  # toggle auto-compute mirror parameters
    oe.F_DEFAULT = 0
    oe.SSOUR = ssour
    oe.SIMAG = simag
    oe.THETA = theta
    oe.FCYL = 1
    oe.FSHAPE = 2
    oe.RWIDX1 = 0.05  # added from oasys # X(+) Half Width / Int Maj Ax [m]
    oe.RWIDX2 = 0.05  # changed from oasys # X(-) Half Width / Int Maj Ax [m]
    oe.RLEN1 = 0.11  # added from oasys # Y(+) Half Width / Int Min Ax [m]
    oe.RLEN2 = 0.11  # changed from oasys # Y(-) Half Width / Int Min Ax [m]
    oe.T_INCIDENCE = theta
    oe.T_REFLECTION = theta
    oe.FWRITE = 0
    oe.T_IMAGE = t_image  # Image plane distance (drift length after mirror)
    oe.T_SOURCE = t_source  # Source plane distance (drift length before mirror)
    oe.F_MOVE = 1
    oe.OFFX = 0.0
    oe.OFFZ = offz
    # oe.Y_ROT = 0
    # oe.Z_ROT = 0
    if mirinfo == 1:
        pkdlog(oe.mirinfo())

    beam.traceOE(oe, oe_num)
    return beam


def shadow_drift_trace(beam, length=900.0):
    """
    This function propagates an input
    beam object through a drift.
    beam: shadow beam object
    length: drift length [cm]
    """

    oe = Shadow.OE()
    oe.DUMMY = 1.0
    # oe.set_empty()
    oe.FWRITE = 3
    oe.T_IMAGE = 0.0
    oe.T_SOURCE = length
    beam.traceOE(oe, 2)

    return beam


def tmat_calc(beam, epsilon):
    """
    This function computes the transfer
    matrix from and input beam object
    containing a propagated central ray
    and 4 offset rays.  It also returns the
    values x, x', z, z' values of the
    central ray.
    epsilon: offset parameter
    """

    # Extract final values of central ray
    x_prop_cen = beam.rays[0, 0]
    xp_prop_cen = beam.rays[0, 3]
    y_prop_cen = beam.rays[0, 0]
    yp_prop_cen = beam.rays[0, 3]
    z_prop_cen = beam.rays[0, 2]
    zp_prop_cen = beam.rays[0, 5]

    # Subtract final central ray values from final deviation vectors
    beam.rays[1, 0] -= x_prop_cen
    beam.rays[1, 2] -= z_prop_cen
    beam.rays[1, 3] -= xp_prop_cen
    beam.rays[1, 5] -= zp_prop_cen
    beam.rays[2, 0] -= x_prop_cen
    beam.rays[2, 2] -= z_prop_cen
    beam.rays[2, 3] -= xp_prop_cen
    beam.rays[2, 5] -= zp_prop_cen
    beam.rays[3, 0] -= x_prop_cen
    beam.rays[3, 2] -= z_prop_cen
    beam.rays[3, 3] -= xp_prop_cen
    beam.rays[3, 5] -= zp_prop_cen
    beam.rays[4, 0] -= x_prop_cen
    beam.rays[4, 2] -= z_prop_cen
    beam.rays[4, 3] -= xp_prop_cen
    beam.rays[4, 5] -= zp_prop_cen

    # Extract final values of off-axis rays
    # x values
    Tmatx0 = beam.rays[1, 0] / epsilon
    Tmatx1 = beam.rays[2, 0] / epsilon
    Tmatx2 = beam.rays[3, 0] / epsilon
    Tmatx3 = beam.rays[4, 0] / epsilon

    # z values
    Tmatz1 = beam.rays[2, 2] / epsilon
    Tmatz0 = beam.rays[1, 2] / epsilon
    Tmatz2 = beam.rays[3, 2] / epsilon
    Tmatz3 = beam.rays[4, 2] / epsilon

    # x' values
    Tmatxp2 = beam.rays[3, 3] / epsilon
    Tmatxp0 = beam.rays[1, 3] / epsilon
    Tmatxp1 = beam.rays[2, 3] / epsilon
    Tmatxp3 = beam.rays[4, 3] / epsilon

    # z' values
    Tmatzp3 = beam.rays[4, 5] / epsilon
    Tmatzp0 = beam.rays[1, 5] / epsilon
    Tmatzp1 = beam.rays[2, 5] / epsilon
    Tmatzp2 = beam.rays[3, 5] / epsilon

    Tmat = np.matrix(
        np.transpose(
            [
                [Tmatx0, Tmatxp0, Tmatz0, Tmatzp0],
                [Tmatx1, Tmatxp1, Tmatz1, Tmatzp1],
                [Tmatx2, Tmatxp2, Tmatz2, Tmatzp2],
                [Tmatx3, Tmatxp3, Tmatz3, Tmatzp3],
            ]
        )
    )

    return Tmat, x_prop_cen, xp_prop_cen, z_prop_cen, zp_prop_cen


# ---
# from https://github.com/radiasoft/rslight/blob/main/Gaussian/gauss_apert-01.py


#  Propagate a 4x4 covariance matrix Sigma through a Gaussian aperture of (Gaussian, not not hard-edge)
#  size parameters a_gx, a_gy
#  NB:  assumed ordering of the variables is x, y, theta_x, theta_y
def gauss_apert_4x4(Sigma, lambda_rad, a_gx, a_gy):
    Sigma_inv = sla.inv(Sigma)
    A = 1.0 * Sigma_inv[0:2, 0:2]
    B = 1.0 * Sigma_inv[0:2, 2:4]
    C = np.transpose(B)
    D = 1.0 * Sigma_inv[2:4, 2:4]

    A_A = np.zeros([2, 2], dtype=np.float32)
    A_A[0, 0] = 2.0 / a_gx**2
    A_A[1, 1] = 2.0 / a_gy**2

    D_inv = sla.inv(D)
    D_A_inv = np.zeros([2, 2], dtype=np.float32)
    D_A_inv[0, 0] = 1.0 / a_gx**2
    D_A_inv[1, 1] = 1.0 / a_gy**2
    D_A_inv *= lambda_rad**2 / (8.0 * np.pi * np.pi)

    D_f = sla.inv(D_inv + D_A_inv)
    BDi = np.matmul(B, D_inv)
    DiC = np.matmul(D_inv, C)  #  == np.transpose(BDi)
    C_f = np.matmul(D_f, DiC)
    B_f = np.transpose(C_f)  #  ==  np.matmul(BDi, D_f)
    A_f = A + A_A - np.matmul(BDi, C) + np.matmul(BDi, np.matmul(D_f, DiC))

    Sigma_inv[0:2, 0:2] = 1.0 * A_f
    Sigma_inv[0:2, 2:4] = 1.0 * B_f
    Sigma_inv[2:4, 0:2] = 1.0 * C_f
    Sigma_inv[2:4, 2:4] = 1.0 * D_f

    return sla.inv(Sigma_inv)
