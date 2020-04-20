# -*- coding: utf-8 -*-
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

from __future__ import print_function #Python 2.7 compatibility
from srwl_bl import *
try:
    import cPickle as pickle
except:
    import pickle
#import time

#*********************************Setting Up Optical Elements and Propagation Parameters
def set_optics(_v):
    """This function describes optical layout of the Coherent Hoard X-ray (CHX) beamline of NSLS-II.
    Such function has to be written for every beamline to be simulated; it is specific to a particular beamline.
    :param _v: structure containing all parameters allowed to be varied for that particular beamline
    """

#---Nominal Positions of Optical Elements [m] (with respect to straight section center)
    zS0 = 33.1798 #White Beam Slits (S0)
    zHFM = 34.2608 #Horizontally-Focusing Mirror M1 (HFM)
    zS1 = 35.6678 #Pink Beam Slits (S1)
    zDCM = 36.4488 #Horizontall-Deflecting Double-Crystal Monochromator (DCM)
    zBPM1 = 38.6904 #BPM-1
    zBPM2 = 50.3872 #BPM-2
    zSSA = 50.6572 #Secondary Source Aperture (SSA)
    zEA = 61.9611 #Energy Absorber (EA)
    zDBPM1 = 62.272 #Diamond BPM-1
    zKBFV = 62.663 #High-Flux Vertically-Focusing KB Mirror M2
    zKBFH = 63.0 #High-Flux Horizontally-Focusing KB Mirror M3
    zSF = 63.3 #High-Flux Sample position (focus of KBF)
    zDBPM2 = 65.9178 #Diamond BPM-2
    zKBRV = 66.113 #High-Resolution Vertically-Focusing KB Mirror M4
    zKBRH = 66.220 #High-Resolution Horizontally-Focusing KB Mirror M5
    zSR = 63.3 #High-Resolution Sample position (focus of KBR)
    #zD = 65 #Detector position (?)

#---Instantiation of the Optical Elements
    arElNamesAll_01 = ['S0', 'S1', 'S1_DCM', 'DCM', 'DCM_SSA', 'SSA', 'SSA_KBFV', 'KBFV', 'KBFV_KBFH', 'KBFH', 'KBFH_zSF']
    arElNamesAll_02 = ['S0', 'S0_HFM', 'HFM', 'HFM_S1', 'S1', 'S1_DCM', 'DCM', 'DCM_SSA', 'SSA', 'SSA_KBRV', 'KBRV', 'KBRV_KBRH', 'KBRH', 'KBRH_zSR']
    arElNamesAll_03 = ['S0', 'S0_HFM', 'HFM', 'HFM_S1', 'S1', 'S1_DCM', 'DCM', 'DCM_SSA', 'SSA', 'SSA_DBPM2', 'DBPM2_KBRV', 'KBRV', 'KBRV_KBRH', 'KBRH', 'KBRH_zSR']
    arElNamesAll_04 = ['S0', 'S0_HFM', 'HFM', 'HFM_S1', 'S1', 'S1_SSA', 'SSA', 'SSA_DBPM2', 'DBPM2_KBRV', 'KBRV', 'KBRV_KBRH', 'KBRH', 'KBRH_zSR']

    arElNamesAll = arElNamesAll_01
    if(_v.op_BL == 2): arElNamesAll = arElNamesAll_02
    elif(_v.op_BL == 3): arElNamesAll = arElNamesAll_03
    elif(_v.op_BL == 4): arElNamesAll = arElNamesAll_04

    '''
    #Treat beamline sub-cases / alternative configurations
    if(len(_v.op_fin) > 0):
        if(_v.op_fin not in arElNamesAll): raise Exception('Optical element with the name specified in the "op_fin" option is not present in this beamline')
        #Could be made more general
    '''

    arElNames = [];
    for i in range(len(arElNamesAll)):
        arElNames.append(arElNamesAll[i])
        if(len(_v.op_fin) > 0):
            if(arElNamesAll[i] == _v.op_fin): break

    el = []; pp = [] #lists of SRW optical element objects and their corresponding propagation parameters

    #S0 (primary slit)
    if('S0' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_S0_dx, _v.op_S0_dy)); pp.append(_v.op_S0_pp)

    #Drift S0 -> HFM
    if('S0_HFM' in arElNames):
        el.append(SRWLOptD(zHFM - zS0)); pp.append(_v.op_S0_HFM_pp)

    #HDM (Height Profile Error)
    if('HFM' in arElNames):
        lenHFM = 0.95 #Length [m]
        horApHFM = lenHFM*_v.op_HFM_ang #Projected dimensions
        verApHFM = 5.e-03 #?

        el.append(SRWLOptA('r', 'a', horApHFM, verApHFM)); pp.append(_v.op_HFMA_pp)

        if(_v.op_HFM_f != 0.):
            el.append(SRWLOptL(_Fx=_v.op_HFM_f)); pp.append(_v.op_HFML_pp)
            #To treat Reflectivity (maybe by Planar Mirror?)
        #elif(_v.op_HFM_r != 0.):
            #Setup Cylindrical Mirror, take into account Reflectivity

        #Height Profile Error
        ifnHFM = os.path.join(_v.fdir, _v.op_HFM_ifn) if len(_v.op_HFM_ifn) > 0 else ''
        if(len(ifnHFM) > 0):
            #hProfDataHFM = srwl_uti_read_data_cols(ifnHFM, '\t', 0, 1)
            hProfDataHFM = srwl_uti_read_data_cols(ifnHFM, '\t')
            opHFM = srwl_opt_setup_surf_height_2d(hProfDataHFM, 'x', _ang=_v.op_HFM_ang, _amp_coef=_v.op_HFM_amp, _nx=1500, _ny=200)
            ofnHFM = os.path.join(_v.fdir, _v.op_HFM_ofn) if len(_v.op_HFM_ofn) > 0 else ''
            if(len(ofnHFM) > 0):
                pathDifHFM = opHFM.get_data(3, 3)
                srwl_uti_save_intens_ascii(pathDifHFM, opHFM.mesh, ofnHFM, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
            el.append(opHFM); pp.append(_v.op_HFMT_pp)

    #Drift HFM -> S1
    if('HFM_S1' in arElNames):
        el.append(SRWLOptD(zS1 - zHFM + _v.op_S1_dz)); pp.append(_v.op_HFM_S1_pp)

    #S1 slit
    if('S1' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_S1_dx, _v.op_S1_dy)); pp.append(_v.op_S1_pp)

    #Drift S1 -> DCM
    if('S1_DCM' in arElNames):
        el.append(SRWLOptD(zDCM - zS1 - _v.op_S1_dz)); pp.append(_v.op_S1_DCM_pp)

    #Drift S1 -> SSA
    if('S1_SSA' in arElNames):
        el.append(SRWLOptD(zSSA - zS1 - _v.op_S1_dz + _v.op_SSA_dz)); pp.append(_v.op_S1_SSA_pp)

    #Double-Crystal Monochromator
    if('DCM' in arElNames):
        tc = 1e-02 # [m] crystal thickness
        angAs = 0.*pi/180. # [rad] asymmetry angle
        hc = [1,1,1]
        if(_v.op_DCM_r == '311'): hc = [3,1,1]

        dc = srwl_uti_cryst_pl_sp(hc, 'Si')
        #print('DCM Interplannar dist.:', dc)
        psi = srwl_uti_cryst_pol_f(_v.op_DCM_e0, hc, 'Si')  #MR15032016: replaced "op_DCM_e" by "op_DCM_e0" to test the import in Sirepo
        #print('DCM Fourier Components:', psi)

        #---------------------- DCM Crystal #1
        opCr1 = SRWLOptCryst(_d_sp=dc, _psi0r=psi[0], _psi0i=psi[1], _psi_hr=psi[2], _psi_hi=psi[3], _psi_hbr=psi[2], _psi_hbi=psi[3], _tc=tc, _ang_as=angAs, _ang_roll=1.5707963, _e_avg=_v.op_DCM_e0)

        #Find appropriate orientation of the Crystal #1 and the Output Beam Frame (using a member-function in SRWLOptCryst):
        orientDataCr1 = opCr1.find_orient(_en=_v.op_DCM_e0, _ang_dif_pl=1.5707963) # Horizontally-deflecting  #MR15032016: replaced "op_DCM_e" by "op_DCM_e0" to test the import in Sirepo
        #Crystal #1 Orientation found:
        orientCr1 = orientDataCr1[0]
        tCr1 = orientCr1[0] #Tangential Vector to Crystal surface
        sCr1 = orientCr1[1]
        nCr1 = orientCr1[2] #Normal Vector to Crystal surface
        # print('DCM Crystal #1 Orientation (original):')
        # print('  t =', tCr1, 's =', orientCr1[1], 'n =', nCr1)

        import uti_math
        if(_v.op_DCM_ac1 != 0): #Small rotation of DCM Crystal #1:
            rot = uti_math.trf_rotation([0,1,0], _v.op_DCM_ac1, [0,0,0])
            tCr1 = uti_math.matr_prod(rot[0], tCr1)
            sCr1 = uti_math.matr_prod(rot[0], sCr1)
            nCr1 = uti_math.matr_prod(rot[0], nCr1)

        #Set the Crystal #1 orientation:
        opCr1.set_orient(nCr1[0], nCr1[1], nCr1[2], tCr1[0], tCr1[1])

        #Orientation of the Outgoing Beam Frame being found:
        orientCr1OutFr = orientDataCr1[1]
        rxCr1 = orientCr1OutFr[0] #Horizontal Base Vector of the Output Beam Frame
        ryCr1 = orientCr1OutFr[1] #Vertical Base Vector of the Output Beam Frame
        rzCr1 = orientCr1OutFr[2] #Longitudinal Base Vector of the Output Beam Frame
        # print('DCM Crystal #1 Outgoing Beam Frame:')
        # print('  ex =', rxCr1, 'ey =', ryCr1, 'ez =', rzCr1)

        #Incoming/Outgoing beam frame transformation matrix for the DCM Crystal #1
        TCr1 = [rxCr1, ryCr1, rzCr1]
        # print('Total transformation matrix after DCM Crystal #1:')
        # uti_math.matr_print(TCr1)
        #print(' ')

        el.append(opCr1); pp.append(_v.op_DCMC1_pp)

        #---------------------- DCM Crystal #2
        opCr2 = SRWLOptCryst(_d_sp=dc, _psi0r=psi[0], _psi0i=psi[1], _psi_hr=psi[2], _psi_hi=psi[3], _psi_hbr=psi[2], _psi_hbi=psi[3], _tc=tc, _ang_as=angAs, _ang_roll=-1.5707963, _e_avg=_v.op_DCM_e0)

        #Find appropriate orientation of the Crystal #2 and the Output Beam Frame
        orientDataCr2 = opCr2.find_orient(_en=_v.op_DCM_e0, _ang_dif_pl=-1.5707963)  #MR15032016: replaced "op_DCM_e" by "op_DCM_e0" to test the import in Sirepo
        #Crystal #2 Orientation found:
        orientCr2 = orientDataCr2[0]
        tCr2 = orientCr2[0] #Tangential Vector to Crystal surface
        sCr2 = orientCr2[1]
        nCr2 = orientCr2[2] #Normal Vector to Crystal surface
        # print('Crystal #2 Orientation (original):')
        # print('  t =', tCr2, 's =', sCr2, 'n =', nCr2)

        if(_v.op_DCM_ac2 != 0): #Small rotation of DCM Crystal #2:
            rot = uti_math.trf_rotation([0,1,0], _v.op_DCM_ac2, [0,0,0])
            tCr2 = uti_math.matr_prod(rot[0], tCr2)
            sCr2 = uti_math.matr_prod(rot[0], sCr2)
            nCr2 = uti_math.matr_prod(rot[0], nCr2)

        #Set the Crystal #2 orientation
        opCr2.set_orient(nCr2[0], nCr2[1], nCr2[2], tCr2[0], tCr2[1])

        #Orientation of the Outgoing Beam Frame being found:
        orientCr2OutFr = orientDataCr2[1]
        rxCr2 = orientCr2OutFr[0] #Horizontal Base Vector of the Output Beam Frame
        ryCr2 = orientCr2OutFr[1] #Vertical Base Vector of the Output Beam Frame
        rzCr2 = orientCr2OutFr[2] #Longitudinal Base Vector of the Output Beam Frame
        # print('DCM Crystal #2 Outgoing Beam Frame:')
        # print('  ex =', rxCr2, 'ey =', ryCr2, 'ez =',rzCr2)

        #Incoming/Outgoing beam transformation matrix for the DCM Crystal #2
        TCr2 = [rxCr2, ryCr2, rzCr2]
        Ttot = uti_math.matr_prod(TCr2, TCr1)
        # print('Total transformation matrix after DCM Crystal #2:')
        # uti_math.matr_print(Ttot)
        #print(' ')

        el.append(opCr2); pp.append(_v.op_DCMC2_pp)

    #Drift DCM -> SSA
    if('DCM_SSA' in arElNames):
        el.append(SRWLOptD(zSSA - zDCM + _v.op_SSA_dz)); pp.append(_v.op_DCM_SSA_pp)

    #SSA slit
    if('SSA' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_SSA_dx, _v.op_SSA_dy)); pp.append(_v.op_SSA_pp)

    #Drift SSA -> DBPM2
    if('SSA_DBPM2' in arElNames):
        el.append(SRWLOptD(zDBPM2 - zSSA - _v.op_SSA_dz + _v.op_DBPM2_dz)); pp.append(_v.op_SSA_DBPM2_pp)

    ###############To continue

##    #Sample
##    if('SMP' in arElNames):
##        ifnSMP = os.path.join(v.fdir, v.op_SMP_ifn) if len(v.op_SMP_ifn) > 0 else ''
##        if(len(ifnSMP) > 0):
##            ifSMP = open(ifnSMP, 'rb')
##            opSMP = pickle.load(ifSMP)
##            ofnSMP = os.path.join(v.fdir, v.op_SMP_ofn) if len(v.op_SMP_ofn) > 0 else ''
##            if(len(ofnSMP) > 0):
##                pathDifSMP = opSMP.get_data(3, 3)
##                srwl_uti_save_intens_ascii(pathDifSMP, opSMP.mesh, ofnSMP, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
##            el.append(opSMP); pp.append(v.op_SMP_pp)
##            ifSMP.close()

##    #Drift Sample -> Detector
##    if('SMP_D' in arElNames):
##        el.append(SRWLOptD(zD - zSample + v.op_D_dz)); pp.append(v.op_SMP_D_pp)

    pp.append(_v.op_fin_pp)

    return SRWLOptC(el, pp)

#*********************************List of Parameters allowed to be varied
#---List of supported options / commands / parameters allowed to be varied for this Beamline (comment-out unnecessary):
varParam = [
#---Data Folder
    ['fdir', 's', os.path.join(os.getcwd(), 'data_SRX'), 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', 'NSLS-II Low Beta ', 'standard electron beam name'],
    ['ebm_nms', 's', 'Day1', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', 0.5, 'electron beam current [A]'],
    #['ebeam_e', 'f', 3., 'electron beam avarage energy [GeV]'],
    ['ebm_de', 'f', 0., 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', 0., 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', 0., 'electron beam initial average vertical position [m]'],
    ['ebm_xp', 'f', 0., 'electron beam initial average horizontal angle [rad]'],
    ['ebm_yp', 'f', 0., 'electron beam initial average vertical angle [rad]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', 0., 'electron beam longitudinal drift [m] to be performed before a required calculation'],
    ['ebm_ens', 'f', -1, 'electron beam relative energy spread'],
    ['ebm_emx', 'f', -1, 'electron beam horizontal emittance [m]'],
    ['ebm_emy', 'f', -1, 'electron beam vertical emittance [m]'],

#---Undulator
    ['und_per', 'f', 0.021, 'undulator period [m]'],
    ['und_len', 'f', 1.5, 'undulator length [m]'],
    ['und_b', 'f', 0.88770981, 'undulator vertical peak magnetic field [T]'],
    #['und_bx', 'f', 0., 'undulator horizontal peak magnetic field [T]'],
    #['und_by', 'f', 1., 'undulator vertical peak magnetic field [T]'],
    #['und_phx', 'f', 1.5708, 'undulator horizontal magnetic field phase [rad]'],
    #['und_phy', 'f', 0., 'undulator vertical magnetic field phase [rad]'],
    ['und_sx', 'i', 1.0, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    #['und_sy', 'i', -1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    ['und_zc', 'f', 1.305, 'undulator center longitudinal position [m]'],

    ['und_mdir', 's', 'magn_meas', 'name of magnetic measurements sub-folder'],
    ['und_mfs', 's', 'ivu21_srx_sum.txt', 'name of magnetic measurements for different gaps summary file'],
    #['und_g', 'f', 0., 'undulator gap [mm] (assumes availability of magnetic measurement or simulation data)'],

#---Calculation Types
    #Electron Trajectory
    ['tr', '', '', 'calculate electron trajectory', 'store_true'],
    ['tr_cti', 'f', 0., 'initial time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_ctf', 'f', 0., 'final time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_np', 'f', 50000, 'number of points for trajectory calculation'],
    ['tr_mag', 'i', 1, 'magnetic field to be used for trajectory calculation: 1- approximate, 2- accurate'],
    ['tr_fn', 's', 'res_trj.dat', 'file name for saving calculated trajectory data'],
    ['tr_pl', 's', 'xxpyypz', 'plot the resulting trajectiry in graph(s): ""- dont plot, otherwise the string should list the trajectory components to plot'],

    #Single-Electron Spectrum vs Photon Energy
    ['ss', '', '', 'calculate single-e spectrum vs photon energy', 'store_true'],
    ['ss_ei', 'f', 100., 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 20000., 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 10000, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_x', 'f', 0., 'horizontal position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_y', 'f', 0., 'vertical position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_meth', 'i', 1, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['ss_prec', 'f', 0.01, 'relative precision for single-e spectrum vs photon energy calculation (nominal value is 0.01)'],
    ['ss_pol', 'i', 6, 'polarization component to extract after spectrum vs photon energy calculation: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['ss_mag', 'i', 1, 'magnetic field to be used for single-e spectrum vs photon energy calculation: 1- approximate, 2- accurate'],
    ['ss_fn', 's', 'res_spec_se.dat', 'file name for saving calculated single-e spectrum vs photon energy'],
    ['ss_pl', 's', 'e', 'plot the resulting single-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],

    #Multi-Electron Spectrum vs Photon Energy (taking into account e-beam emittance, energy spread and collection aperture size)
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
    ['sm_hf', 'i', 15, 'final UR spectral harmonic to be taken into accountfor multi-e spectrum vs photon energy calculation'],
    ['sm_prl', 'f', 1., 'longitudinal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_pra', 'f', 1., 'azimuthal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_type', 'i', 1, 'calculate flux (=1) or flux per unit surface (=2)'],
    ['sm_pol', 'i', 6, 'polarization component to extract after calculation of multi-e flux or intensity: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['sm_fn', 's', 'res_spec_me.dat', 'file name for saving calculated milti-e spectrum vs photon energy'],
    ['sm_pl', 's', 'e', 'plot the resulting spectrum-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],
    #to add options for the multi-e calculation from "accurate" magnetic field

    #Power Density Distribution vs horizontal and vertical position
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

    #Single-Electron Intensity distribution vs horizontal and vertical position
    ['si', '', '', 'calculate single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position', 'store_true'],
    #Single-Electron Wavefront Propagation
    ['ws', '', '', 'calculate single-electron (/ fully coherent) wavefront propagation', 'store_true'],
    #Multi-Electron (partially-coherent) Wavefront Propagation
    ['wm', '', '', 'calculate multi-electron (/ partially coherent) wavefront propagation', 'store_true'],

    ['w_e', 'f', 9000., 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1., 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', 0., 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', 2.4e-03, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 100, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', 0., 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', 2.0e-03, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 100, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', 1., 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', 1, 'method to use for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_prec', 'f', 0.01, 'relative precision for calculation of intensity distribution vs horizontal and vertical position'],
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

    #['ws_fn', 's', '', 'file name for saving single-e (/ fully coherent) wavefront data'],
    #['wm_fn', 's', '', 'file name for saving multi-e (/ partially coherent) wavefront data'],
    #to add options

    ['op_r', 'f', 33.1798, 'longitudinal position of the first optical element [m]'],
    ['op_fin', 's', 'S3_SMP', 'name of the final optical element wavefront has to be propagated through'],

    #NOTE: the above option/variable names (fdir, ebm*, und*, ss*, sm*, pw*, is*, ws*, wm*) should be the same in all beamline scripts
    #on the other hand, the beamline optics related options below (op*) are specific to a particular beamline (and can be differ from beamline to beamline).
    #However, the default values of all the options/variables (above and below) can differ from beamline to beamline.

#---Beamline Optics
    ['op_BL', 'f', 1, 'beamline version/option number'],

    ['op_S0_dx', 'f', 2.375e-03, 'slit S0: horizontal size [m]'],
    ['op_S0_dy', 'f', 2.0e-03, 'slit S0: vertical size [m]'],

    ['op_HFM_f', 'f', 11.0893, 'mirror HFM: focal length [m] (effective if op_HFM_f != 0)'],
    ['op_HFM_r', 'f', 8.924e+03, 'mirror HFM: radius of curvature [m] (effective if op_HFM_r != 0 and op_HFM_f == 0)'],
    ['op_HFM_ang', 'f', 2.5e-03, 'mirror HFM: angle of incidence [rad]'],
    ['op_HFM_mat', 's', '', 'mirror HFM: coating material; possible options: Si, Cr, Rh, Pt'],
    ['op_HFM_ifn', 's', 'mir_metro/SRX_HFM_height_prof.dat', 'mirror HFM: input file name of height profile data'],
    #['op_HFM_ifn', 's', '', 'mirror HFM: input file name of height profile data'],
    ['op_HFM_amp', 'f', 1., 'mirror HFM: amplification coefficient for height profile data'],
    ['op_HFM_ofn', 's', 'res_SRX_HFM_opt_path_dif.dat', 'mirror HCM: output file name of optical path difference data'],

    ['op_S1_dz', 'f', 0., 'S1: offset of longitudinal position [m]'],
    ['op_S1_dx', 'f', 2.375e-03, 'slit S1: horizontal size [m]'],
    ['op_S1_dy', 'f', 10.0e-03, 'slit S1: vertical size [m]'],

    ['op_DCM_e0', 'f', 8999., 'DCM: central photon energy DCM is tuned to [eV]'],  #MR15032016: replaced "op_DCM_e" by "op_DCM_e0" to test the import in Sirepo
    ['op_DCM_r', 's', '111', 'DCM: reflection type (can be either "111" or "311")'],
    ['op_DCM_ac1', 'f', 0., 'DCM: angular deviation of 1st crystal from exact Bragg angle [rad]'],
    ['op_DCM_ac2', 'f', 0., 'DCM: angular deviation of 2nd crystal from exact Bragg angle [rad]'],

    ['op_SSA_dz', 'f', 0., 'slit SSA: offset of longitudinal position [m]'],
    ['op_SSA_dx', 'f', 3.0e-03, 'slit SSA: horizontal size [m]'],
    ['op_SSA_dy', 'f', 3.0e-03, 'slit SSA: vertical size [m]'],

    ['op_DBPM2_dz', 'f', 0., 'slit DBPM2: offset of longitudinal position [m]'],

    ###############To continue

##    ['op_SMP_dz', 'f', 0., 'sample: offset of longitudinal position [m]'],
##    ['op_SMP_ifn', 's', 'CHX_SMP_CDI_001.pickle', 'sample: model file name (binary "dumped" SRW transmission object)'],
##    ['op_SMP_ofn', 's', 'res_CHX_SMP_opt_path_dif.dat', 'sample: output file name of optical path difference data'],
##    ['op_D_dz', 'f', 0., 'detector: offset of longitudinal position [m]'],

    #to add options for different beamline cases, etc.

    #Propagation Param.:    [0][1][2][3][4] [5]  [6]  [7] [8] [9][10][11]
    #['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 4.5, 5.0, 1.5, 2.5, 0, 0, 0], 'slit S0: propagation parameters'],
    #['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 2.2, 6.0, 3.0, 15.0, 0, 0, 0], 'slit S0: propagation parameters'],
    #['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 2.0, 15.0,1.5, 15.0,0, 0, 0], 'slit S0: propagation parameters'],
    ['op_S0_pp', 'f',       [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S0: propagation parameters'],
    ['op_S0_HFM_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S0 -> HFM: propagation parameters'],
    ['op_HFMA_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HCM: Aperture propagation parameters'],
    ['op_HFML_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HCM: Lens propagation parameters'],
    ['op_HFMT_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HCM: Transmission propagation parameters'],
    ['op_HFM_S1_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift HDM -> S1: propagation parameters'],
    ['op_S1_pp', 'f',       [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S1: propagation parameters'],
    ['op_S1_SSA_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> SSA: propagation parameters'],
    ['op_S1_DCM_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> DCM: propagation parameters'],
    ['op_DCMC1_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM C1: propagation parameters'],
    ['op_DCMC2_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM C2: propagation parameters'],
    ['op_DCM_SSA_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift DCM -> SSA: propagation parameters'],
    ['op_SSA_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit SSA: propagation parameters'],
    ['op_SSA_DBPM2_pp', 'f',[0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift SSA -> DBPM2: propagation parameters'],

    ###############To continue

##    ['op_S3_SMP_pp', 'f',  [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S3 -> sample: propagation parameters'],
##    ['op_SMP_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'sample: propagation parameters'],
##    ['op_SMP_D_pp', 'f',   [0, 0, 1, 3, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'sample -> detector: propagation parameters'],

    #['op_fin_pp', 'f',     [0, 0, 1, 0, 1, 0.1, 5.0, 1.0, 1.5, 0, 0, 0], 'final post-propagation (resize) parameters'],
    ['op_fin_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'final post-propagation (resize) parameters'],

    #[ 0]: Auto-Resize (1) or not (0) Before propagation
    #[ 1]: Auto-Resize (1) or not (0) After propagation
    #[ 2]: Relative Precision for propagation with Auto-Resizing (1. is nominal)
    #[ 3]: Allow (1) or not (0) for semi-analytical treatment of the quadratic (leading) phase terms at the propagation
    #[ 4]: Do any Resizing on Fourier side, using FFT, (1) or not (0)
    #[ 5]: Horizontal Range modification factor at Resizing (1. means no modification)
    #[ 6]: Horizontal Resolution modification factor at Resizing
    #[ 7]: Vertical Range modification factor at Resizing
    #[ 8]: Vertical Resolution modification factor at Resizing
    #[ 9]: Type of wavefront Shift before Resizing (not yet implemented)
    #[10]: New Horizontal wavefront Center position after Shift (not yet implemented)
    #[11]: New Vertical wavefront Center position after Shift (not yet implemented)
    #[12]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Horizontal Coordinate
    #[13]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Vertical Coordinate
    #[14]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Longitudinal Coordinate
    #[15]: Optional: Orientation of the Horizontal Base vector of the Output Frame in the Incident Beam Frame: Horizontal Coordinate
    #[16]: Optional: Orientation of the Horizontal Base vector of the Output Frame in the Incident Beam Frame: Vertical Coordinate
]

varParam = srwl_uti_ext_options(varParam) #Adding other default options

#*********************************Entry
if __name__ == "__main__":

#---Parse options, defining Beamline elements and running calculations
    v = srwl_uti_parse_options(varParam)

#---Add some constant "parameters" (not allowed to be varied) for the beamline
    v.und_per = 0.021 #['und_per', 'f', 0.021, 'undulator period [m]'],
    v.und_len = 1.5 #['und_len', 'f', 1.5, 'undulator length [m]'],
    v.und_zc = 1.305 #['und_zc', 'f', 1.305, 'undulator center longitudinal position [m]'],
    v.und_sy = -1 #['und_sy', 'i', -1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    v.und_sx = 1 #['und_sx', 'i', 1, 'undulator vertical magnetic field symmetry vs longitudinal position'],

#---Setup optics only if Wavefront Propagation is required:
    v.ws = True
    op = set_optics(v) if(v.ws or v.wm) else None

#---Run all requested calculations
    SRWLBeamline('SRX beamline').calc_all(v, op)
