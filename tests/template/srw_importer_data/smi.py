#############################################################################
# SRWLIB Example: Virtual Beamline: a set of utilities and functions allowing to simulate
# operation of an SR Beamline.
# The standard use of this script is from command line, with some optional arguments,
# e.g. for calculation (with default parameter values) of:
# UR Spectrum Through a Slit (Flux within a default aperture):
#    python SRWLIB_VirtBL_*.py --sm
# Single-Electron UR Spectrum (Flux per Unit Surface):
#    python SRWLIB_VirtBL_*.py --ss
# UR Power Density (at the first optical element):
#    python SRWLIB_VirtBL_*.py --pw
# Input Single-Electron UR Intensity Distribution (at the first optical element):
#    python SRWLIB_VirtBL_*.py --si
# Single-Electron Wavefront Propagation:
#    python SRWLIB_VirtBL_*.py --ws
# Multi-Electron Wavefront Propagation:
#  Sequential Mode:
#    python SRWLIB_VirtBL_*.py --wm
#  Parallel Mode (using MPI / mpi4py), e.g.:
#    mpiexec -n 6 python SRWLIB_VirtBL_*.py --wm
# For changing parameters of all these calculaitons from the default valuse, see the definition
# of all options in the list at the end of the script.
# v 0.04
#############################################################################


from srwpy.srwl_bl import *

try:
    import cPickle as pickle
except:
    import pickle


# *********************************Setting Up Optical Elements and Propagation Parameters
def set_optics(_v):
    """This function describes optical layout of the SMI beamline of NSLS-II.
    Such function has to be written for every beamline to be simulated; it is specific to a particular beamline.

    :param _v: structure containing all parameters allowed to be varied for that particular beamline.
    :return SRWLOptC(): container object.
    """

    # Nominal Positions of Optical Elements [m] (with respect to straight section center)
    zStart = _v.op_r
    zAPE = zStart
    zMOAT = zStart + 2.44
    zHFM = zStart + 2.44 + 2.94244
    zVFM = zStart + 2.44 + 2.94244 + 3.42
    zVM = zStart + 2.44 + 2.94244 + 3.42 + 0.7
    zSSA = zStart + 2.44 + 2.94244 + 3.42 + 0.7 + 8.0
    zES1 = zStart + 2.44 + 2.94244 + 3.42 + 0.7 + 8.0 + 3.9
    zCRL = zStart + 2.44 + 2.94244 + 3.42 + 0.7 + 8.0 + 10.33492
    zES2 = zStart + 2.44 + 2.94244 + 3.42 + 0.7 + 8.0 + 10.33492 + 1.66508

    # Instantiation of the Optical Elements:
    msg = 'The combination of beamline={} / bump={} / BMmode={}'
    print(msg.format(_v.beamline, _v.bump, _v.BMmode))
    msg += ' is not supported.'
    if _v.beamline == 'ES1':
        if not _v.bump:
            arElNamesAll_01 = ['D_APE_HFM', 'HFML', 'D_HFM_VFM', 'VFML', 'D_VFM_SSA', 'SSA', 'D_SSA_ES1']
        else:
            if _v.BMmode == 'Norm':
                arElNamesAll_01 = ['D_APE_MOA', 'MOAT', 'D_MOA_HFM', 'HFML', 'HFMT', 'D_HFM_VFM', 'VFML', 'VFMT',
                                   'D_VFM_VM', 'VMT', 'D_VM_SSA', 'SSA', 'D_SSA_ES1']
            else:
                raise Exception(msg.format(_v.beamline, _v.bump, _v.BMmode))
    elif _v.beamline == 'ES2':
        if not _v.bump:
            raise Exception(msg.format(_v.beamline, _v.bump, _v.BMmode))
        else:
            if _v.BMmode == 'LowDiv':  # focus ES2 without Kb with low divergence
                arElNamesAll_01 = ['D_APE_MOA', 'MOAT', 'D_MOA_HFM', 'HFML', 'HFMT', 'D_HFM_VFM', 'VFML', 'VFMT',
                                   'D_VFM_VM', 'VMT', 'D_VM_SSA', 'SSA', 'D_SSA_CRL', 'ApCRL', 'CRL', 'D_CRL_ES2']
            elif _v.BMmode == 'Norm':
                arElNamesAll_01 = ['D_APE_MOA', 'MOAT', 'D_MOA_HFM', 'HFML', 'HFMT', 'D_HFM_VFM', 'VFML', 'VFMT',
                                   'D_VFM_VM', 'VMT', 'D_VM_SSA', 'SSA', 'D_SSA_CRL', 'ApCRL', 'CRL', 'D_CRL_ES2']
            else:
                raise Exception(msg.format(_v.beamline, _v.bump, _v.BMmode))
    else:
        raise Exception(msg.format(_v.beamline, _v.bump, _v.BMmode))

    arElNamesAll_02 = []
    arElNamesAll_03 = []
    arElNamesAll_04 = []

    arElNamesAll = arElNamesAll_01
    if _v.op_BL == 2:
        arElNamesAll = arElNamesAll_02
    elif _v.op_BL == 3:
        arElNamesAll = arElNamesAll_03
    elif _v.op_BL == 4:
        arElNamesAll = arElNamesAll_04

    # Treat beamline sub-cases / alternative configurations
    if len(_v.op_fin) > 0:
        if _v.op_fin not in arElNamesAll:
            raise Exception('Optical element with the name specified in the "op_fin" option is not present in this beamline')

    arElNames = []
    for i in range(len(arElNamesAll)):
        arElNames.append(arElNamesAll[i])
        if len(_v.op_fin) > 0:
            if arElNamesAll[i] == _v.op_fin:
                break

    # Lists of SRW optical element objects and their corresponding propagation parameters
    el = []
    pp = []

    for i in range(len(arElNames)):
        # Process all drifts here:
        if arElNames[i] == 'D_APE_MOA':
            el.append(SRWLOptD(zMOAT - zAPE))
            if _v.beamline == 'ES1':
                pp.append(_v.op_APE_MOA_es1_pp)
            elif _v.beamline == 'ES2':
                pp.append(_v.op_APE_MOA_es2_pp)
        elif arElNames[i] == 'D_MOA_HFM':
            el.append(SRWLOptD(zHFM - zMOAT))
            pp.append(_v.op_MOA_HFM_pp)
        elif arElNames[i] == 'D_HFM_VFM':
            el.append(SRWLOptD(zVFM - zHFM))
            pp.append(_v.op_HFM_VFM_pp)
        elif arElNames[i] == 'D_VFM_VM':
            el.append(SRWLOptD(zVM - zVFM))
            pp.append(_v.op_VFM_VM_pp)
        elif arElNames[i] == 'D_VM_SSA':
            el.append(SRWLOptD(zSSA - zVM))
            pp.append(_v.op_VM_SSA_pp)
        elif arElNames[i] == 'D_SSA_CRL':
            el.append(SRWLOptD(zCRL - zSSA))
            pp.append(_v.op_SSA_CRL_pp)
        elif arElNames[i] == 'D_CRL_ES2':
            el.append(SRWLOptD(zES2 - zCRL))
            pp.append(_v.op_CRL_ES2_pp)
        elif arElNames[i] == 'D_SSA_ES1':
            el.append(SRWLOptD(zES1 - zSSA))
            pp.append(_v.op_SSA_ES1_pp)
        elif arElNames[i] == 'D_APE_HFM':
            el.append(SRWLOptD(zHFM - zAPE))
            if _v.beamline == 'ES1':
                pp.append(_v.op_APE_MOA_es1_pp)
            elif _v.beamline == 'ES2':
                pp.append(_v.op_APE_MOA_es2_pp)
        elif arElNames[i] == 'D_VFM_SSA':
            el.append(SRWLOptD(zSSA - zVFM))
            pp.append(_v.op_VFM_SSA_pp)


        elif arElNames[i] == 'MOAT':
            ifnMOAT = os.path.join(_v.fdir, _v.op_MOAT_ifn) if len(_v.op_MOAT_ifn) > 0 else ''
            if len(ifnMOAT) > 0 and os.path.isfile(ifnMOAT):
                hProfDataMOAT = srwl_uti_read_data_cols(ifnMOAT, '\t')
                opMOAT = srwl_opt_setup_surf_height_1d(hProfDataMOAT, 'y', _ang=0.09727, _nx=100, _ny=500,
                                                       _size_x=2.0e-02,
                                                       _size_y=16e-3 * sin(0.09727))
                ofnMOAT = os.path.join(_v.fdir, _v.op_MOAT_ofn) if len(_v.op_MOAT_ofn) > 0 else ''
                if len(ofnMOAT) > 0:
                    pathDifMOAT = opMOAT.get_data(3, 3)
                    srwl_uti_save_intens_ascii(pathDifMOAT, opMOAT.mesh, ofnMOAT, 0,
                                               ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'],
                                               _arUnits=['', 'm', 'm', 'm'])
                el.append(opMOAT)
                pp.append(_v.op_MOAT_pp)

        elif arElNames[i] == 'HFML':
            if _v.BMmode == 'Norm':
                el.append(SRWLOptL(_Fx=1. / (1. / zHFM + 1. / ((zVFM - zHFM) + (zSSA - zVFM) + (zES1 - zSSA)))))  # to focus at ES1
            elif _v.BMmode == 'LowDiv':
                el.append(SRWLOptL(_Fx=1. / (1. / zHFM + 1. / ((zVFM - zHFM) + (zSSA - zVFM) + (zES1 - zSSA) + 8.1 - 0.3))))  # to focus at ES2 with a low divergence
            pp.append(_v.op_HFML_pp)

        elif arElNames[i] == 'HFMT':
            ifnHFM = os.path.join(_v.fdir, _v.op_HFM_ifn) if len(_v.op_HFM_ifn) > 0 else ''
            if len(ifnHFM) > 0:
                hProfDataHFM = srwl_uti_read_data_cols(ifnHFM, '\t')
                opHFM = srwl_opt_setup_surf_height_1d(hProfDataHFM, 'x', _ang=_v.op_HFM_ang, _amp_coef=_v.op_HFM_amp,
                                                      _nx=803, _ny=200, _size_x=0.5 * sin(3.1415927e-03),
                                                      _size_y=6.0e-03)
                ofnHFM = os.path.join(_v.fdir, _v.op_HFM_ofn) if len(_v.op_HFM_ofn) > 0 else ''
                if len(ofnHFM) > 0:
                    pathDifHFM = opHFM.get_data(3, 3)
                    srwl_uti_save_intens_ascii(pathDifHFM, opHFM.mesh, ofnHFM, 0,
                                               ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'],
                                               _arUnits=['', 'm', 'm', 'm'])
                el.append(opHFM)
                pp.append(_v.op_HFMT_pp)

        elif arElNames[i] == 'VFML':
            if _v.BMmode == 'Norm':
                # Focus at ES1; if using Bump, VFM must be 3.9+0.3 m (to compensate bump which moves focus 0.2 m upstream):
                el.append(SRWLOptL(_Fy=1. / (1. / (zVFM - 0.6) + 1. / ((zSSA - zVFM) + (zES1 - zSSA) + 0.3))))
            elif _v.BMmode == 'LowDiv':
                # Focus at ES2 with a low divergence:
                el.append(SRWLOptL(_Fy=1. / (1. / (zVFM - 0.6) + 1. / ((zSSA - zVFM) + (zES1 - zSSA) - 5.7 + 8.1))))
            pp.append(_v.op_VFML_pp)

        elif arElNames[i] == 'VFMT':
            ifnVFM = os.path.join(_v.fdir, _v.op_VFM_ifn) if len(_v.op_VFM_ifn) > 0 else ''
            if len(ifnVFM) > 0:
                hProfDataVFM = srwl_uti_read_data_cols(ifnVFM, '\t')
                opVFM = srwl_opt_setup_surf_height_1d(hProfDataVFM, 'y', _ang=3.1415927e-03, _nx=200, _ny=288,
                                                      _size_x=6.0e-03, _size_y=0.4 * sin(3.1415927e-03))
                ofnVFM = os.path.join(_v.fdir, _v.op_VFM_ofn) if len(_v.op_VFM_ofn) > 0 else ''
                if len(ofnVFM) > 0:
                    pathDifVFM = opVFM.get_data(3, 3)
                    srwl_uti_save_intens_ascii(pathDifVFM, opVFM.mesh, ofnVFM, 0,
                                               ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'],
                                               _arUnits=['', 'm', 'm', 'm'])
                el.append(opVFM)
                pp.append(_v.op_VFMT_pp)

        elif arElNames[i] == 'VMT':
            ifnVM = os.path.join(_v.fdir, _v.op_VM_ifn) if len(_v.op_VM_ifn) > 0 else ''
            if len(ifnVM) > 0:
                hProfDataVM = srwl_uti_read_data_cols(ifnVM, '\t')
                # sinusoidal equal to HFM. the original spec is 0.1, 6.75e-09 both 'h' 'v', angle 6.1086524e-03 rad to correct for vertical.
                opVM = srwl_opt_setup_surf_height_1d(hProfDataVM, 'y', _ang=3.1415927e-03, _nx=200, _ny=500,
                                                     _size_x=6.0e-03, _size_y=0.5 * sin(3.1415927e-03))
                ofnVM = os.path.join(_v.fdir, _v.op_VM_ofn) if len(_v.op_VM_ofn) > 0 else ''
                if len(ofnVM) > 0:
                    pathDifVM = opVM.get_data(3, 3)
                    srwl_uti_save_intens_ascii(pathDifVM, opVM.mesh, ofnVM, 0,
                                               ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'],
                                               _arUnits=['', 'm', 'm', 'm'])
                el.append(opVM)
                pp.append(_v.op_VMT_pp)

        elif arElNames[i] == 'SSA':
            # SSA = SRWLOptA('r', 'a', 0.4e-03, 0.4e-03)  # 0.4, 0.4 for NOT low divergence mode;
            if _v.beamline == 'ES1' and _v.BMmode == 'Norm':
                el.append(SRWLOptA('r', 'a', _v.op_SSA_es1_norm_dx, _v.op_SSA_es1_norm_dy))
            elif _v.beamline == 'ES2' and _v.BMmode == 'Norm':
                el.append(SRWLOptA('r', 'a', _v.op_SSA_es2_norm_dx, _v.op_SSA_es2_norm_dy))
            elif _v.beamline == 'ES2' and _v.BMmode == 'LowDiv':
                el.append(SRWLOptA('r', 'a', _v.op_SSA_es2_lowdiv_dx, _v.op_SSA_es2_lowdiv_dy))
            pp.append(_v.op_SSA_pp)

        elif arElNames[i] == 'ApCRL':
            # ApCRL = SRWLOptA('c', 'a', 1.0e-3)
            el.append(SRWLOptA('c', 'a', _v.op_ApCRL_r))
            pp.append(_v.op_ApCRL_pp)

        elif arElNames[i] == 'CRL':
            '''
            from Delta import Delta, DEFAULTS_FILE
            delta_obj = Delta(
                energy=_v.w_e,
                precise=True,
                data_file=os.path.join(os.path.dirname(os.path.dirname(DEFAULTS_FILE)), 'dat/Be_delta.dat'),
                quiet=True
            )
            delta = delta_obj.delta  # 8.21692879E-07  # Be @ 20.4KeV
            '''
            delta = 8.21692879E-07
            attenLen = 28544.7e-06  # [m] #20.4KeV
            diamCRL = 1.e-03  # CRL diameter
            rMinCRL = 50e-06  # CRL radius at the tip of parabola [m]
            nCRL = 23  # number of lenses
            wallThickCRL = 32.4e-06  # CRL wall thickness [m]

            el.append(srwl_opt_setup_CRL(3, delta, attenLen, 1, diamCRL, diamCRL, rMinCRL, nCRL, wallThickCRL, 0, 0))
            pp.append(_v.op_CRL_pp)
        else:
            raise Exception(f'Processing for element "{arElNames[i]}" is not included yet.')

    pp.append(_v.op_fin_pp)
    return SRWLOptC(el, pp)


# ********************************* List of Parameters allowed to be varied
# List of supported options / commands / parameters allowed to be varied for this Beamline (comment-out unnecessary):
varParam = [
    # Beamline version:
    ['beamline', 's', 'ES2', 'beamline codename (can be "ES1"/"ES2")'],
    ['BMmode', 's', 'Norm', 'beamline BM mode (can be "Norm"/"LowDiv")'],
    ['bump', '', '', 'use bump or not', 'store_true'],

    # Data Folder
    ['fdir', 's', os.path.join(os.getcwd(), 'smi204crlb'), 'folder (directory) name for reading-in input and saving output data files'],

    # Electron Beam
    ['ebm_nm', 's', 'NSLS-II High Beta ', 'standard electron beam name'],
    ['ebm_nms', 's', 'Day 1', 'standard electron beam name suffix: e.g. can be Day 1, Final'],
    ['ebm_i', 'f', 0.5, 'electron beam current [A]'],
    # ['ebeam_e', 'f', 3., 'electron beam avarage energy [GeV]'],
    ['ebm_de', 'f', 0., 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', 0., 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', 0., 'electron beam initial average vertical position [m]'],
    ['ebm_xp', 'f', 0., 'electron beam initial average horizontal angle [rad]'],
    ['ebm_yp', 'f', 0., 'electron beam initial average vertical angle [rad]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', -1.44325, 'electron beam longitudinal drift [m] to be performed before a required calculation'],
    ['ebm_ens', 'f', -1, 'electron beam relative energy spread'],
    ['ebm_emx', 'f', -1, 'electron beam horizontal emittance [m]'],
    ['ebm_emy', 'f', -1, 'electron beam vertical emittance [m]'],

    # Undulator
    ['und_per', 'f', 0.023, 'undulator period [m]'],
    ['und_len', 'f', 2.7945, 'undulator length [m]'],
    ['und_b', 'f', 0.955, 'undulator vertical peak magnetic field [T]'],
    # ['und_bx', 'f', 0., 'undulator horizontal peak magnetic field [T]'],
    # ['und_by', 'f', 1., 'undulator vertical peak magnetic field [T]'],
    # ['und_phx', 'f', 1.5708, 'undulator horizontal magnetic field phase [rad]'],
    ['und_phy', 'f', 0., 'undulator vertical magnetic field phase [rad]'],
    ['und_sx', 'i', 1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    ['und_sy', 'i', -1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    ['und_zc', 'f', 0.6, 'undulator center longitudinal position [m]'],

    ['und_mdir', 's', 'magn_meas', 'name of magnetic measurements sub-folder'],
    ['und_mfs', 's', 'ivu21_srx_sum.txt', 'name of magnetic measurements for different gaps summary file'],
    # ['und_g', 'f', 0., 'undulator gap [mm] (assumes availability of magnetic measurement or simulation data)'],

    # Calculation Types
    # Electron Trajectory
    ['tr', '', '', 'calculate electron trajectory', 'store_true'],
    ['tr_cti', 'f', 0., 'initial time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_ctf', 'f', 0., 'final time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_np', 'f', 50000, 'number of points for trajectory calculation'],
    ['tr_mag', 'i', 1, 'magnetic field to be used for trajectory calculation: 1- approximate, 2- accurate'],
    ['tr_fn', 's', 'res_trj.dat', 'file name for saving calculated trajectory data'],
    ['tr_pl', 's', 'xxpyypz', 'plot the resulting trajectiry in graph(s): ""- dont plot, otherwise the string should list the trajectory components to plot'],

    # Single-Electron Spectrum vs Photon Energy
    ['ss', '', '', 'calculate single-e spectrum vs photon energy', 'store_true'],
    ['ss_ei', 'f', 20000., 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 20400., 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 10000, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_x', 'f', 0., 'horizontal position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_y', 'f', 0., 'vertical position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_meth', 'i', 1, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['ss_prec', 'f', 0.008, 'relative precision for single-e spectrum vs photon energy calculation (nominal value is 0.01)'],
    ['ss_pol', 'i', 6, 'polarization component to extract after spectrum vs photon energy calculation: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['ss_mag', 'i', 1, 'magnetic field to be used for single-e spectrum vs photon energy calculation: 1- approximate, 2- accurate'],
    ['ss_fn', 's', 'res_spec_se.dat', 'file name for saving calculated single-e spectrum vs photon energy'],
    ['ss_pl', 's', 'e', 'plot the resulting single-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],

    # Multi-Electron Spectrum vs Photon Energy (taking into account e-beam emittance, energy spread and collection aperture size)
    ['sm', '', '', 'calculate multi-e spectrum vs photon energy', 'store_true'],
    ['sm_ei', 'f', 100., 'initial photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ef', 'f', 20000., 'final photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ne', 'i', 10000, 'number of points vs photon energy for multi-e spectrum vs photon energy calculation'],
    ['sm_x', 'f', 0., 'horizontal center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_rx', 'f', 0.001, 'range of horizontal position / horizontal aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_nx', 'i', 1, 'number of points vs horizontal position for multi-e spectrum vs photon energy calculation'],
    ['sm_y', 'f', 0., 'vertical center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ry', 'f', 0.001, 'range of vertical position / vertical aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ny', 'i', 1, 'number of points vs vertical position for multi-e spectrum vs photon energy calculation'],
    ['sm_mag', 'i', 1, 'magnetic field to be used for calculation of multi-e spectrum spectrum or intensity distribution: 1- approximate, 2- accurate'],
    ['sm_hi', 'i', 1, 'initial UR spectral harmonic to be taken into accountfor multi-e spectrum vs photon energy calculation'],
    ['sm_hf', 'i', 21, 'final UR spectral harmonic to be taken into accountfor multi-e spectrum vs photon energy calculation'],
    ['sm_prl', 'f', 1., 'longitudinal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_pra', 'f', 1., 'azimuthal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_type', 'i', 1, 'calculate flux (=1) or flux per unit surface (=2)'],
    ['sm_pol', 'i', 6, 'polarization component to extract after calculation of multi-e flux or intensity: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['sm_fn', 's', 'res_spec_me.dat', 'file name for saving calculated milti-e spectrum vs photon energy'],
    ['sm_pl', 's', 'e', 'plot the resulting spectrum-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],
    # to add options for the multi-e calculation from "accurate" magnetic field

    # Power Density Distribution vs horizontal and vertical position
    ['pw', '', '', 'calculate SR power density distribution', 'store_true'],
    ['pw_x', 'f', 0., 'central horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_rx', 'f', 0.015, 'range of horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_nx', 'i', 100, 'number of points vs horizontal position for calculation of power density distribution'],
    ['pw_y', 'f', 0., 'central vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ry', 'f', 0.015, 'range of vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ny', 'i', 100, 'number of points vs vertical position for calculation of power density distribution'],
    ['pw_pr', 'f', 1., 'precision factor for calculation of power density distribution'],
    ['pw_meth', 'i', 1, 'power density computation method (1- "near field", 2- "far field")'],
    ['pw_zi', 'f', 0., 'initial longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_zf', 'f', 0., 'final longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_mag', 'i', 1, 'magnetic field to be used for power density calculation: 1- approximate, 2- accurate'],
    ['pw_fn', 's', 'res_pow.dat', 'file name for saving calculated power density distribution'],
    ['pw_pl', 's', 'xy', 'plot the resulting power density distribution in a graph: ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    # Single-Electron Intensity distribution vs horizontal and vertical position
    ['si', '', '', 'calculate single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position', 'store_true'],
    # Single-Electron Wavefront Propagation
    ['ws', '', '', 'calculate single-electron (/ fully coherent) wavefront propagation', 'store_true'],
    # Multi-Electron (partially-coherent) Wavefront Propagation
    ['wm', '', '', 'calculate multi-electron (/ partially coherent) wavefront propagation', 'store_true'],

    ['w_e', 'f', 20358., 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1., 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', 0., 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', 2.4e-03, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 100, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', 0., 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', 2.0e-03, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 100, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', 0., 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', 1, 'method to use for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_prec', 'f', 0.008, 'relative precision for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_mag', 'i', 1, 'magnetic field to be used for calculation of intensity distribution vs horizontal and vertical position: 1- approximate, 2- accurate'],
    ['si_pol', 'i', 6, 'polarization component to extract after calculation of intensity distribution: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['si_type', 'i', 0, 'type of a characteristic to be extracted after calculation of intensity distribution: 0- Single-Electron Intensity, 1- Multi-Electron Intensity, 2- Single-Electron Flux, 3- Multi-Electron Flux, 4- Single-Electron Radiation Phase, 5- Re(E): Real part of Single-Electron Electric Field, 6- Im(E): Imaginary part of Single-Electron Electric Field, 7- Single-Electron Intensity, integrated over Time or Photon Energy'],

    ['si_fn', 's', 'res_int_se.dat', 'file name for saving calculated single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position'],
    ['ws_fni', 's', 'res_int_pr_se.dat', 'file name for saving propagated single-e intensity distribution vs horizontal and vertical position'],
    ['ws_pl', 's', 'xy', 'plot the propagated radiaiton intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],
    ['ws_ap', 'i', 0, 'switch specifying representation of the resulting Stokes parameters (/ Intensity distribution): coordinate (0) or angular (1)'],
    ['si_pl', 's', 'xy', 'plot the input intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    ['wm_nm', 'i', 100000, 'number of macro-electrons (coherent wavefronts) for calculation of multi-electron wavefront propagation'],
    ['wm_na', 'i', 5, 'number of macro-electrons (coherent wavefronts) to average on each node at parallel (MPI-based) calculation of multi-electron wavefront propagation'],
    ['wm_ns', 'i', 5, 'saving periodicity (in terms of macro-electrons / coherent wavefronts) for intermediate intensity at multi-electron wavefront propagation calculation'],
    ['wm_ch', 'i', 0, 'type of a characteristic to be extracted after calculation of multi-electron wavefront propagation: #0- intensity (s0); 1- four Stokes components; 2- mutual intensity cut vs x; 3- mutual intensity cut vs y'],
    ['wm_ap', 'i', 0, 'switch specifying representation of the resulting Stokes parameters: coordinate (0) or angular (1)'],
    ['wm_x0', 'f', 0, 'horizontal center position for mutual intensity cut calculation'],
    ['wm_y0', 'f', 0, 'vertical center position for mutual intensity cut calculation'],
    ['wm_ei', 'i', 0, 'integration over photon energy is required (1) or not (0); if the integration is required, the limits are taken from w_e, w_ef'],
    ['wm_rm', 'i', 1, 'method for generation of pseudo-random numbers for e-beam phase-space integration: 1- standard pseudo-random number generator, 2- Halton sequences, 3- LPtau sequences (to be implemented)'],
    ['wm_fni', 's', 'res_int_pr_me.dat', 'file name for saving propagated multi-e intensity distribution vs horizontal and vertical position'],

    # ['ws_fn', 's', '', 'file name for saving single-e (/ fully coherent) wavefront data'],
    # ['wm_fn', 's', '', 'file name for saving multi-e (/ partially coherent) wavefront data'],
    # to add options

    ['op_r', 'f', 29.5, 'longitudinal position of the first optical element [m]'],
    ['op_fin', 's', '', 'name of the final optical element wavefront has to be propagated through'],

    # NOTE: the above option/variable names (fdir, ebm*, und*, ss*, sm*, pw*, is*, ws*, wm*) should be the same in all beamline scripts
    # on the other hand, the beamline optics related options below (op*) are specific to a particular beamline (and can be differ from beamline to beamline).
    # However, the default values of all the options/variables (above and below) can differ from beamline to beamline.

    # ---Beamline Optics
    ['op_BL', 'f', 1, 'beamline version/option number'],

    # MOAT: first mirror of Monocromator error shape
    ['op_MOAT_ifn', 's', 'Si_heat204.dat', 'MOAT: input file name of height profile data'],
    ['op_MOAT_ofn', 's', 'res_er_mono_NEW.dat', 'MOAT: output file name of optical path difference data'],

    ['op_ApCRL_r', 'f', 1.0e-3, 'radius of the CRL aperture'],

    ['op_S0_dx', 'f', 2.375e-03, 'slit S0: horizontal size [m]'],
    ['op_S0_dy', 'f', 2.0e-03, 'slit S0: vertical size [m]'],

    ['op_HFM_f', 'f', 11.0893, 'mirror HFM: focal length [m] (effective if op_HFM_f != 0)'],
    ['op_HFM_r', 'f', 8.924e+03, 'mirror HFM: radius of curvature [m] (effective if op_HFM_r != 0 and op_HFM_f == 0)'],
    ['op_HFM_ang', 'f', 3.1415927e-03, 'mirror HFM: angle of incidence [rad]'],
    ['op_HFM_mat', 's', '', 'mirror HFM: coating material; possible options: Si, Cr, Rh, Pt'],
    ['op_HFM_ifn', 's', 'HFM_SESO.dat', 'mirror HFM: input file name of height profile data'],
    ['op_VFM_ifn', 's', 'VFM_SESO.dat', 'mirror VFM: input file name of height profile data'],
    ['op_VM_ifn', 's', 'VM03rms.dat', 'mirror VM: input file name of height profile data'],

    ['op_HFM_amp', 'f', 1., 'mirror HFM: amplification coefficient for height profile data'],
    ['op_HFM_ofn', 's', 'res_er_HFM_NEW.dat', 'mirror HFM: output file name of optical path difference data'],
    ['op_VFM_ofn', 's', 'res_er_VFM_NEW.dat', 'mirror VFM: output file name of optical path difference data'],
    ['op_VM_ofn', 's', 'res_er_VM_NEW.dat', 'mirror VFM: output file name of optical path difference data'],

    ['op_S1_dz', 'f', 0., 'S1: offset of longitudinal position [m]'],
    ['op_S1_dx', 'f', 2.375e-03, 'slit S1: horizontal size [m]'],
    ['op_S1_dy', 'f', 10.0e-03, 'slit S1: vertical size [m]'],

    # MR15032016: replaced "op_DCM_e" by "op_DCM_e0" to test the import in Sirepo:
    ['op_DCM_e0', 'f', 20358., 'DCM: central photon energy DCM is tuned to [eV]'],
    ['op_DCM_r', 's', '111', 'DCM: reflection type (can be either "111" or "311")'],
    ['op_DCM_ac1', 'f', 0., 'DCM: angular deviation of 1st crystal from exact Bragg angle [rad]'],
    ['op_DCM_ac2', 'f', 0., 'DCM: angular deviation of 2nd crystal from exact Bragg angle [rad]'],

    ['op_SSA_dz', 'f', 0., 'slit SSA: offset of longitudinal position [m]'],
    ['op_SSA_es1_norm_dx', 'f', 0.4e-03, 'slit SSA: horizontal size [m]'],
    ['op_SSA_es1_norm_dy', 'f', 0.4e-03, 'slit SSA: vertical size [m]'],
    ['op_SSA_es2_norm_dx', 'f', 0.9e-03, 'slit SSA: horizontal size [m]'],
    ['op_SSA_es2_norm_dy', 'f', 0.9e-03, 'slit SSA: vertical size [m]'],
    ['op_SSA_es2_lowdiv_dx', 'f', 0.9e-03, 'slit SSA: horizontal size [m]'],
    ['op_SSA_es2_lowdiv_dy', 'f', 0.9e-03, 'slit SSA: vertical size [m]'],

    ['op_DBPM2_dz', 'f', 0., 'slit DBPM2: offset of longitudinal position [m]'],

    ###############To continue

    ##    ['op_SMP_dz', 'f', 0., 'sample: offset of longitudinal position [m]'],
    ##    ['op_SMP_ifn', 's', 'CHX_SMP_CDI_001.pickle', 'sample: model file name (binary "dumped" SRW transmission object)'],
    ##    ['op_SMP_ofn', 's', 'res_CHX_SMP_opt_path_dif.dat', 'sample: output file name of optical path difference data'],
    ##    ['op_D_dz', 'f', 0., 'detector: offset of longitudinal position [m]'],

    # to add options for different beamline cases, etc.

    # Propagation Param.:    [0][1][2][3][4] [5]  [6]  [7] [8] [9][10][11]
    # ['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 4.5, 5.0, 1.5, 2.5, 0, 0, 0], 'slit S0: propagation parameters'],
    # ['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 2.2, 6.0, 3.0, 15.0, 0, 0, 0], 'slit S0: propagation parameters'],
    # ['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 2.0, 15.0,1.5, 15.0,0, 0, 0], 'slit S0: propagation parameters'],
    ['op_MOAT_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'MOAT: propagation parameters'],
    ['op_APE_MOA_es1_pp', 'f', [0, 0, 1.0, 2, 0, 8.0, 3.0, 2.0, 3.0, 0, 0, 0], 'drift S0   -> MOAT: propagation parameters'],
    ['op_APE_MOA_es2_pp', 'f', [0, 0, 1.0, 2, 0, 8.0, 3.0, 3.0, 4.0, 0, 0, 0], 'drift S0   -> MOAT: propagation parameters'],
    ['op_MOA_HFM_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift MOAT -> HFM:  propagation parameters'],
    ['op_HFM_VFM_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift HFM  -> VFM:  propagation parameters'],
    ['op_VFML_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift VFML -> '],

    ['op_VFMT_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift VFMT -> SSA:  propagation parameters'],
    ['op_VFM_VM_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift VFM  -> VM:   propagation parameters'],
    ['op_VMT_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift VMT  -> SSA:  propagation parameters'],
    ['op_VM_SSA_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],
    ['op_SSA_CRL_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],
    ['op_ApCRL_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],
    ['op_CRL_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],
    ['op_CRL_ES2_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],
    ['op_SSA_ES1_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],
    ['op_VFM_SSA_pp', 'f', [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], ''],

    ['op_HFML_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HCM: Lens propagation parameters'],
    ['op_HFMT_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HCM: Transmission propagation parameters'],
    ['op_SSA_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit SSA: propagation parameters'],

    # ['op_S0_pp', 'f',       [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S0: propagation parameters'],
    # ['op_S0_HFM_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S0 -> HFM: propagation parameters'],
    # ['op_HFMA_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HCM: Aperture propagation parameters'],
    # ['op_HFM_S1_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift HDM -> S1: propagation parameters'],
    # ['op_S1_pp', 'f',       [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S1: propagation parameters'],
    # ['op_S1_SSA_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> SSA: propagation parameters'],
    # ['op_S1_DCM_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> DCM: propagation parameters'],
    # ['op_DCMC1_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM C1: propagation parameters'],
    # ['op_DCMC2_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM C2: propagation parameters'],
    # ['op_DCM_SSA_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift DCM -> SSA: propagation parameters'],
    # ['op_SSA_DBPM2_pp', 'f',[0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift SSA -> DBPM2: propagation parameters'],

    ###############To continue

    ##    ['op_S3_SMP_pp', 'f',  [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S3 -> sample: propagation parameters'],
    ##    ['op_SMP_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'sample: propagation parameters'],
    ##    ['op_SMP_D_pp', 'f',   [0, 0, 1, 3, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'sample -> detector: propagation parameters'],

    # ['op_fin_pp', 'f',     [0, 0, 1, 0, 1, 0.1, 5.0, 1.0, 1.5, 0, 0, 0], 'final post-propagation (resize) parameters'],
    ['op_fin_pp', 'f', [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'final post-propagation (resize) parameters'],

    # [ 0]: Auto-Resize (1) or not (0) Before propagation
    # [ 1]: Auto-Resize (1) or not (0) After propagation
    # [ 2]: Relative Precision for propagation with Auto-Resizing (1. is nominal)
    # [ 3]: Allow (1) or not (0) for semi-analytical treatment of the quadratic (leading) phase terms at the propagation
    # [ 4]: Do any Resizing on Fourier side, using FFT, (1) or not (0)
    # [ 5]: Horizontal Range modification factor at Resizing (1. means no modification)
    # [ 6]: Horizontal Resolution modification factor at Resizing
    # [ 7]: Vertical Range modification factor at Resizing
    # [ 8]: Vertical Resolution modification factor at Resizing
    # [ 9]: Type of wavefront Shift before Resizing (not yet implemented)
    # [10]: New Horizontal wavefront Center position after Shift (not yet implemented)
    # [11]: New Vertical wavefront Center position after Shift (not yet implemented)
    # [12]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Horizontal Coordinate
    # [13]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Vertical Coordinate
    # [14]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Longitudinal Coordinate
    # [15]: Optional: Orientation of the Horizontal Base vector of the Output Frame in the Incident Beam Frame: Horizontal Coordinate
    # [16]: Optional: Orientation of the Horizontal Base vector of the Output Frame in the Incident Beam Frame: Vertical Coordinate
]

varParam = srwl_uti_ext_options(varParam)  # Adding other default options

# *********************************Entry
if __name__ == "__main__":
    # ---Parse options, defining Beamline elements and running calculations
    v = srwl_uti_parse_options(varParam)

    '''
    #---Add some constant "parameters" (not allowed to be varied) for the beamline
    v.und_per = 0.021 #['und_per', 'f', 0.021, 'undulator period [m]'],
    v.und_len = 1.5 #['und_len', 'f', 1.5, 'undulator length [m]'],
    v.und_zc = 1.305 #['und_zc', 'f', 1.305, 'undulator center longitudinal position [m]'],
    v.und_sy = -1 #['und_sy', 'i', -1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    v.und_sx = 1 #['und_sx', 'i', 1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    '''
    # ---Setup optics only if Wavefront Propagation is required:
    v.si = True
    v.ss = True
    v.ws = True
    op = set_optics(v) if (v.ws or v.wm) else None

    # ---Run all requested calculations
    SRWLBeamline('SMI beamline').calc_all(v, op)
