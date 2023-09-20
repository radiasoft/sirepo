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
# v 0.07
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
    zS0 = 20.5 #S0 (primary slit)
    zHDM = 27.4 #Horizontally-Deflecting Mirror (HDM)
    zS1 = 29.9 #S1 slit
    zDCM = 31.6 #DCM (vertically-deflecting)
    zS2 = 34.3 #S2 slit
    zBPM = 34.6 #BPM for beam visualization
    zCRL = 35.4 #+tzCRL*1e-3 #CRL transfocator (corrected by translation)
    zKL = 45.0 #44.5 #+tzKL*1e-3 #Kinoform Lens for horizontal focusing (corrected by translation)
    zS3 = 48.0 #S3 slit ('pinhole', waist position)
    zSample = 48.7 #Sample position, COR of diffractometer
    zD = 58.7 #Detector position

#---Instantiation of the Optical Elements
    arElNamesAllOpt = [
    ['S0', 'S0_S1', 'S1', 'S1_S2', 'S2', 'S2_BPM', 'BPM_CRL', 'CRL1', 'CRL2', 'CRL_KL', 'KLA', 'KL', 'KL_S3', 'S3', 'S3_SMP', 'SMP', 'SMP_D'], #1
    ['S0', 'S0_HDM', 'HDM', 'HDM_S1', 'S1', 'S1_S2', 'S2', 'S2_CRL', 'CRL1', 'CRL2', 'CRL_SMP'], #2
    ['S0', 'S0_HDM', 'HDM', 'HDM_S1', 'S1', 'S1_DCM', 'DCM', 'DCM_S2', 'S2', 'S2_CRL', 'CRL1', 'CRL2', 'CRL_KL', 'KLA', 'KL', 'KL_S3', 'S3', 'SMP', 'SMP_D'], #3
    ['S0', 'S0_HDM', 'HDM', 'HDM_S1', 'S1', 'S1_DCM', 'DCM', 'DCM_S2', 'S2', 'S2_CRL', 'CRL1', 'CRL2', 'CRL_SMP'], #4
    ['S0', 'S0_HDM', 'HDM', 'HDM_S1', 'S1', 'S1_DCM', 'DCM', 'DCM_S2', 'S2', 'S2_CRL', 'FIB', 'CRL_SMP'], #5
    ]
    arElNamesAll = arElNamesAllOpt[int(round(_v.op_BL - 1))]

    if(len(_v.op_fin) > 0):
        if(_v.op_fin not in arElNamesAll): raise Exception('Optical element with the name specified in the "op_fin" option is not present in this beamline')
        #Could be made more general

    arElNames = [];
    for i in range(len(arElNamesAll)):
        arElNames.append(arElNamesAll[i])
        if(len(_v.op_fin) > 0):
            if(arElNamesAll[i] == _v.op_fin): break

    el = []; pp = [] #lists of SRW optical element objects and their corresponding propagation parameters

    #S0 (primary slit)
    if('S0' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_S0_dx, _v.op_S0_dy, _v.op_S0_x, _v.op_S0_y)); pp.append(_v.op_S0_pp)

    #Drift S0 -> HDM
    if('S0_HDM' in arElNames):
        el.append(SRWLOptD(zHDM - zS0)); pp.append(_v.op_S0_HDM_pp)

    #Drift S0 -> S1
    if('S0_S1' in arElNames):
        el.append(SRWLOptD(zS1 - zS0)); pp.append(_v.op_S0_S1_pp)

    #HDM (Height Profile Error)
    if('HDM' in arElNames):
        horApHDM = 0.94e-03 #Projected dimensions
        verApHDM = 1.e-03
        angHDM = 3.1415926e-03 #? grazing angle
        ifnHDM = os.path.join(_v.fdir, _v.op_HDM_ifn) if len(_v.op_HDM_ifn) > 0 else ''
        if(len(ifnHDM) > 0):
            hProfDataHDM = srwl_uti_read_data_cols(ifnHDM, '\t', 0, 1)
            opHDM = srwl_opt_setup_surf_height_1d(hProfDataHDM, 'x', _ang=angHDM, _amp_coef=_v.op_HDM_amp, _nx=1000, _ny=200, _size_x=horApHDM, _size_y=verApHDM, _xc=_v.op_HDM_x, _yc=_v.op_HDM_y)
            ofnHDM = os.path.join(_v.fdir, _v.op_HDM_ofn) if len(_v.op_HDM_ofn) > 0 else ''
            if(len(ofnHDM) > 0):
                pathDifHDM = opHDM.get_data(3, 3)
                srwl_uti_save_intens_ascii(pathDifHDM, opHDM.mesh, ofnHDM, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
            el.append(opHDM); pp.append(_v.op_HDM_pp)

    #Drift HDM -> S1
    if('HDM_S1' in arElNames):
        el.append(SRWLOptD(zS1 - zHDM + _v.op_S1_dz)); pp.append(_v.op_HDM_S1_pp)

    #S1 slit
    if('S1' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_S1_dx, _v.op_S1_dy, _v.op_S1_x, _v.op_S1_y)); pp.append(_v.op_S1_pp)

    #Drift S1 -> DCM
    if('S1_DCM' in arElNames):
        el.append(SRWLOptD(zDCM - zS1)); pp.append(_v.op_S1_DCM_pp)

    #Double-Crystal Monochromator
    tCr1 = [0, 0, -1] #required for surface error
    if('DCM' in arElNames):
        tc = 1e-02 # [m] crystal thickness
        angAs = 0.*3.1415926/180. # [rad] asymmetry angle
        hc = [1,1,1]
        dc = srwl_uti_cryst_pl_sp(hc, 'Si')
        #print('DCM Interplannar dist.:', dc)
        psi = srwl_uti_cryst_pol_f(_v.op_DCM_e, hc, 'Si')
        #print('DCM Fourier Components:', psi)

        #---------------------- DCM Crystal #1
        opCr1 = SRWLOptCryst(_d_sp=dc, _psi0r=psi[0], _psi0i=psi[1], _psi_hr=psi[2], _psi_hi=psi[3], _psi_hbr=psi[2], _psi_hbi=psi[3], _tc=tc, _ang_as=angAs)

        #Find appropriate orientation of the Crystal #1 and the Output Beam Frame (using a member-function in SRWLOptCryst):
        #orientDataCr1 = opCr1.find_orient(_en=_v.op_DCM_e, _ang_dif_pl=1.5707963) # Horizontally-deflecting (from HXN)
        orientDataCr1 = opCr1.find_orient(_en=_v.op_DCM_e) # Vertically-deflecting

        #Crystal #1 Orientation found:
        orientCr1 = orientDataCr1[0]
        tCr1 = orientCr1[0] #Tangential Vector to Crystal surface
        sCr1 = orientCr1[1] #Sagital Vector to Crystal surface
        nCr1 = orientCr1[2] #Normal Vector to Crystal surface
        print('DCM Crystal #1 Orientation (original):')
        print('  t =', tCr1, 's =', orientCr1[1], 'n =', nCr1)

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
        print('DCM Crystal #1 Outgoing Beam Frame:')
        print('  ex =', rxCr1, 'ey =', ryCr1, 'ez =', rzCr1)

        #Incoming/Outgoing beam frame transformation matrix for the DCM Crystal #1
        TCr1 = [rxCr1, ryCr1, rzCr1]
        print('Total transformation matrix after DCM Crystal #1:')
        uti_math.matr_print(TCr1)
        #print(' ')

        el.append(opCr1); pp.append(_v.op_DCMC1_pp)

        #---------------------- DCM Crystal #2
        opCr2 = SRWLOptCryst(_d_sp=dc, _psi0r=psi[0], _psi0i=psi[1], _psi_hr=psi[2], _psi_hi=psi[3], _psi_hbr=psi[2], _psi_hbi=psi[3], _tc=tc, _ang_as=angAs, _ang_roll=3.1415926)

        #Find appropriate orientation of the Crystal #2 and the Output Beam Frame
        #orientDataCr2 = opCr2.find_orient(_en=_v.op_DCM_e, _ang_dif_pl=-1.5707963) #from HXN
        orientDataCr2 = opCr2.find_orient(_en=_v.op_DCM_e, _ang_dif_pl=3.1415926) #Vertically-deflecting

        #Crystal #2 Orientation found:
        orientCr2 = orientDataCr2[0]
        tCr2 = orientCr2[0] #Tangential Vector to Crystal surface
        sCr2 = orientCr2[1]
        nCr2 = orientCr2[2] #Normal Vector to Crystal surface
        print('Crystal #2 Orientation (original):')
        print('  t =', tCr2, 's =', sCr2, 'n =', nCr2)

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
        print('DCM Crystal #2 Outgoing Beam Frame:')
        print('  ex =', rxCr2, 'ey =', ryCr2, 'ez =',rzCr2)

        #Incoming/Outgoing beam transformation matrix for the DCM Crystal #2
        TCr2 = [rxCr2, ryCr2, rzCr2]
        Ttot = uti_math.matr_prod(TCr2, TCr1)
        print('Total transformation matrix after DCM Crystal #2:')
        uti_math.matr_print(Ttot)
        #print(' ')

        el.append(opCr2); pp.append(_v.op_DCMC2_pp)

    #DCM Surface Error
    horApDCM = 2.e-03 #Projected dimensions
    verApDCM = 2.e-03
    angDCM = asin(abs(tCr1[2])) #Grazing angle to crystal surface
    ifnDCME = os.path.join(_v.fdir, _v.op_DCME_ifn) if len(_v.op_DCME_ifn) > 0 else ''
    if(len(ifnDCME) > 0):
        hProfDataDCME = srwl_uti_read_data_cols(ifnDCME, '\t', 0, 1)
        opDCME = srwl_opt_setup_surf_height_1d(hProfDataDCME, 'y', _ang=angDCM, _amp_coef=_v.op_DCME_amp, _nx=1000, _ny=200, _size_x=horApDCM, _size_y=verApDCM, _xc=_v.op_DCME_x, _yc=_v.op_DCME_y)
        ofnDCME = os.path.join(_v.fdir, _v.op_DCME_ofn) if len(_v.op_DCME_ofn) > 0 else ''
        if(len(ofnDCME) > 0):
            pathDifDCME = opDCME.get_data(3, 3)
            srwl_uti_save_intens_ascii(pathDifDCME, opDCME.mesh, ofnDCME, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
        el.append(opDCME); pp.append(_v.op_DCME_pp)

    #Drift DCM -> S2
    if('DCM_S2' in arElNames):
        el.append(SRWLOptD(zS2 - zDCM + _v.op_S2_dz)); pp.append(_v.op_DCM_S2_pp)

    #Boron Fiber (with Tungsten core)
    if('FIB' in arElNames):
        fpln = 3 #focusing in both planes
        if((_v.op_FIB_fpl == 'h') or (_v.op_FIB_fpl == 'H') or (_v.op_FIB_fpl == 'x') or (_v.op_FIB_fpl == 'X')): fpln = 1
        elif((_v.op_FIB_fpl == 'v') or (_v.op_FIB_fpl == 'V') or (_v.op_FIB_fpl == 'y') or (_v.op_FIB_fpl == 'Y')): fpln = 2

        el.append(srwl_opt_setup_cyl_fiber(fpln, _v.op_FIB_delta_e, _v.op_FIB_delta_c, _v.op_FIB_atnl_e, _v.op_FIB_atnl_c, _v.op_FIB_d_e, _v.op_FIB_d_c, _v.op_FIB_x, _v.op_FIB_y))
        pp.append(_v.op_FIB_pp)

    #Drift S1 -> S2
    if('S1_S2' in arElNames):
        el.append(SRWLOptD(zS2 - zS1 + _v.op_S2_dz)); pp.append(_v.op_S1_S2_pp)

    #S2 slit
    if('S2' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_S2_dx, _v.op_S2_dy, _v.op_S2_x, _v.op_S2_y)); pp.append(_v.op_S2_pp)

    #Drift S2 -> BPM
    if('S2_BPM' in arElNames):
        el.append(SRWLOptD(zBPM - zS2 + _v.op_BPM_dz)); pp.append(_v.op_S2_BPM_pp)

    #Drift BPM -> CRL
    if('BPM_CRL' in arElNames):
        el.append(SRWLOptD(zCRL - zBPM + _v.op_CRL_dz)); pp.append(_v.op_BPM_CRL_pp)

    #Drift S2 -> CRL
    if('S2_CRL' in arElNames):
        el.append(SRWLOptD(zCRL - zS2 - _v.op_S2_dz + _v.op_CRL_dz)); pp.append(_v.op_S2_CRL_pp)

    #CRL1 (1D, vertically-focusing)
    if('CRL1' in arElNames):
        if((_v.op_CRL1_n > 0) and (_v.op_CRL1_fpl != '')):
            fpln = 3 #focusing in both planes
            if((_v.op_CRL1_fpl == 'h') or (_v.op_CRL1_fpl == 'H') or (_v.op_CRL1_fpl == 'x') or (_v.op_CRL1_fpl == 'X')): fpln = 1
            elif((_v.op_CRL1_fpl == 'v') or (_v.op_CRL1_fpl == 'V') or (_v.op_CRL1_fpl == 'y') or (_v.op_CRL1_fpl == 'Y')): fpln = 2

            el.append(srwl_opt_setup_CRL(fpln, _v.op_CRL1_delta, _v.op_CRL1_atnl, 1, _v.op_CRL1_apnf, _v.op_CRL1_apf, _v.op_CRL1_rmin, _v.op_CRL1_n, _v.op_CRL1_thck, _v.op_CRL1_x, _v.op_CRL1_y))
            pp.append(_v.op_CRL1_pp)

    #CRL2 (1D, vertically-focusing)
    if('CRL2' in arElNames):
        if((_v.op_CRL2_n > 0) and (_v.op_CRL2_fpl != '')):
            fpln = 3 #focusing in both planes
            if((_v.op_CRL2_fpl == 'h') or (_v.op_CRL2_fpl == 'H') or (_v.op_CRL2_fpl == 'x') or (_v.op_CRL2_fpl == 'X')): fpln = 1
            elif((_v.op_CRL2_fpl == 'v') or (_v.op_CRL2_fpl == 'V') or (_v.op_CRL2_fpl == 'y') or (_v.op_CRL2_fpl == 'Y')): fpln = 2

            el.append(srwl_opt_setup_CRL(fpln, _v.op_CRL2_delta, _v.op_CRL2_atnl, 1, _v.op_CRL2_apnf, _v.op_CRL2_apf, _v.op_CRL2_rmin, _v.op_CRL2_n, _v.op_CRL2_thck, _v.op_CRL2_x, _v.op_CRL2_y))
            pp.append(_v.op_CRL2_pp)

    #Drift CRL -> KL
    if('CRL_KL' in arElNames):
        el.append(SRWLOptD(zKL - zCRL - _v.op_CRL_dz + _v.op_KL_dz)); pp.append(_v.op_CRL_KL_pp)

    #Drift CRL -> Sample
    if('CRL_SMP' in arElNames):
        el.append(SRWLOptD(zSample - zCRL - _v.op_CRL_dz + _v.op_SMP_dz)); pp.append(_v.op_CRL_SMP_pp)

    #KL Aperture
    if('KLA' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_KLA_dx, _v.op_KLA_dy, _v.op_KL_x, _v.op_KL_y)); pp.append(_v.op_KLA_pp)

    #KL (1D, horizontally-focusing)
    if('KL' in arElNames):
        el.append(SRWLOptL(_v.op_KL_fx, _v.op_KL_fy, _v.op_KL_x, _v.op_KL_y)) #KL as Ideal Lens; to make it a transmission element with a profile read from a file
        pp.append(_v.op_KL_pp)

    #Drift KL -> S3
    if('KL_S3' in arElNames):
        el.append(SRWLOptD(zS3 - zKL + _v.op_S3_dz)); pp.append(_v.op_KL_S3_pp)

    #S3 slit
    if('S3' in arElNames):
        el.append(SRWLOptA('r', 'a', _v.op_S3_dx, _v.op_S3_dy, _v.op_S3_x, _v.op_S3_y)); pp.append(_v.op_S3_pp)

    #Drift S3 -> Sample
    if('S3_SMP' in arElNames):
        el.append(SRWLOptD(zSample - zS3 + _v.op_SMP_dz)); pp.append(_v.op_S3_SMP_pp)

    #Sample
    if('SMP' in arElNames):
        ifnSMP = os.path.join(_v.fdir, _v.op_SMP_ifn) if len(_v.op_SMP_ifn) > 0 else ''
        if(len(ifnSMP) > 0):
            ifSMP = open(ifnSMP, 'rb')
            opSMP = pickle.load(ifSMP)

            #Implementing transverse shift of sample ??
            xSt = opSMP.mesh.xStart
            xFi = opSMP.mesh.xFin
            halfRangeX = 0.5*(xFi - xSt)
            opSMP.mesh.xStart = -halfRangeX + _v.op_SMP_x
            opSMP.mesh.xFin = halfRangeX + _v.op_SMP_x
            ySt = opSMP.mesh.yStart
            yFi = opSMP.mesh.yFin
            halfRangeY = 0.5*(yFi - ySt)
            opSMP.mesh.yStart = -halfRangeY + _v.op_SMP_y
            opSMP.mesh.yFin = halfRangeY + _v.op_SMP_y

            ofnSMP = os.path.join(_v.fdir, _v.op_SMP_ofn) if len(_v.op_SMP_ofn) > 0 else ''
            if(len(ofnSMP) > 0):
                pathDifSMP = opSMP.get_data(3, 3)
                srwl_uti_save_intens_ascii(pathDifSMP, opSMP.mesh, ofnSMP, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
            el.append(opSMP); pp.append(_v.op_SMP_pp)
            ifSMP.close()

    #Drift Sample -> Detector
    if('SMP_D' in arElNames):
        el.append(SRWLOptD(zD - zSample + _v.op_D_dz)); pp.append(_v.op_SMP_D_pp)

    pp.append(_v.op_fin_pp)

    return SRWLOptC(el, pp)

#*********************************List of Parameters allowed to be varied
#---List of supported options / commands / parameters allowed to be varied for this Beamline (comment-out unnecessary):
varParam = [
#---Data Folder
    ['fdir', 's', os.path.join(os.getcwd(), 'data_CHX'), 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', 'NSLS-II Low Beta ', 'standard electron beam name'],
    ['ebm_nms', 's', 'Day1', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', 0.5, 'electron beam current [A]'],
    ['ebm_de', 'f', 0., 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', 0., 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', 0., 'electron beam initial average vertical position [m]'],
    ['ebm_xp', 'f', 0., 'electron beam initial average horizontal angle [rad]'],
    ['ebm_yp', 'f', 0., 'electron beam initial average vertical angle [rad]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', -1.7, 'electron beam longitudinal drift [m] to be performed before a required calculation'],
    ['ebm_ens', 'f', -1, 'electron beam relative energy spread'],
    ['ebm_emx', 'f', -1, 'electron beam horizontal emittance [m]'],
    ['ebm_emy', 'f', -1, 'electron beam vertical emittance [m]'],

#---Undulator
    ['und_per', 'f', 0.02, 'undulator period [m]'],
    ['und_len', 'f', 3., 'undulator length [m]'],
    ['und_b', 'f', 0.88770981, 'undulator vertical peak magnetic field [T]'],
    #['und_bx', 'f', 0., 'undulator horizontal peak magnetic field [T]'],
    #['und_by', 'f', 1., 'undulator vertical peak magnetic field [T]'],
    #['und_phx', 'f', 1.5708, 'undulator horizontal magnetic field phase [rad]'],
    #['und_phy', 'f', 0., 'undulator vertical magnetic field phase [rad]'],
    ['und_sx', 'i', 1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    ['und_sy', 'i', -1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    ['und_zc', 'f', 0., 'undulator center longitudinal position [m]'],

    ['und_mdir', 's', 'magn_meas', 'name of magnetic measurements sub-folder'],
    ['und_mfs', 's', 'ivu20_chx_sum.txt', 'name of magnetic measurements for different gaps summary file'],
    #['und_g', 'f', 0., 'undulator gap [mm] (assumes availability of magnetic measurement or simulation data)'],

    #NOTE: the above option/variable names (fdir, ebm*, und*, ss*, sm*, pw*, is*, ws*, wm*) should be the same in all beamline scripts
    #on the other hand, the beamline optics related options below (op*) are specific to a particular beamline (and can be differ from beamline to beamline).
    #However, the default values of all the options/variables (above and below) can differ from beamline to beamline.

#---Beamline Optics

    ['op_r', 'f', 20.5, 'longitudinal position of the first optical element [m]'],
    ['op_fin', 's', 'FIB', 'name of the final optical element wavefront has to be propagated through'],

    ['op_BL', 'f', 5, 'beamline version/option number'],

    ['op_S0_dx', 'f', 0.2e-03, 'slit S0: horizontal size [m]'],
    ['op_S0_dy', 'f', 1.0e-03, 'slit S0: vertical size [m]'],
    ['op_S0_x', 'f', 0., 'slit S0: horizontal center position [m]'],
    ['op_S0_y', 'f', 0., 'slit S0: vertical center position [m]'],

    ['op_HDM_ifn', 's', 'CHX_HDM_height_prof_1d.dat', 'mirror HDM: input file name of height profile data'],
    ['op_HDM_amp', 'f', 1., 'mirror HDM: amplification coefficient for height profile data'],
    ['op_HDM_ofn', 's', 'res_CHX_HDM_opt_path_dif.dat', 'mirror HDM: output file name of optical path difference data'],
    ['op_HDM_x', 'f', 0., 'mirror HDM surface error: horizontal center position [m]'],
    ['op_HDM_y', 'f', 0., 'mirror HDM surface error: vertical center position [m]'],

    ['op_S1_dz', 'f', 0., 'S1: offset of longitudinal position [m]'],
    ['op_S1_dx', 'f', 0.2e-03, 'slit S1: horizontal size [m]'],
    ['op_S1_dy', 'f', 1.0e-03, 'slit S1: vertical size [m]'],
    ['op_S1_x', 'f', 0., 'slit S1: horizontal center position [m]'],
    ['op_S1_y', 'f', 0., 'slit S1: vertical center position [m]'],

    ['op_DCM_e', 'f', 9000., 'DCM: central photon energy DCM is tuned to [eV]'],
    ['op_DCM_ac1', 'f', 0., 'DCM: angular deviation of 1st crystal from exact Bragg angle [rad]'],
    ['op_DCM_ac2', 'f', 0., 'DCM: angular deviation of 2nd crystal from exact Bragg angle [rad]'],

    ['op_DCME_ifn', 's', 'CHX_DCM_height_prof_1d.dat', 'DCM surface error: input file name of height profile data'],
    ['op_DCME_amp', 'f', 1., 'DCM surface error: amplification coefficient'],
    ['op_DCME_ofn', 's', 'res_CHX_DCM_opt_path_dif.dat', 'DCM surface error: output file name of optical path difference data'],
    ['op_DCME_x', 'f', 0., 'DCM surface error: horizontal center position [m]'],
    ['op_DCME_y', 'f', 0., 'DCM surface error: vertical center position [m]'],

    ['op_FIB_fpl', 's', '', 'FIB: focusing plane ("h" or "v" or "hv" or "")'],
    ['op_FIB_delta_e', 'f', 4.20756805e-06, 'Fiber: refractive index decrement of main (exterior) material'],
    ['op_FIB_delta_c', 'f', 4.20756805e-06, 'Fiber: refractive index decrement of core material'],
    ['op_FIB_atnl_e', 'f', 7312.94e-06, 'Fiber: attenuation length of main (exterior) material [m]'],
    ['op_FIB_atnl_c', 'f', 7312.94e-06, 'Fiber: attenuation length of core material [m]'],
    ['op_FIB_d_e', 'f', 100.e-06, 'Fiber: ext. diameter [m]'],
    ['op_FIB_d_c', 'f', 10.e-06, 'Fiber: core diameter [m]'],
    ['op_FIB_x', 'f', 0., 'Fiber: horizontal center position [m]'],
    ['op_FIB_y', 'f', 0., 'Fiber: vertical center position [m]'],

    ['op_S2_dz', 'f', 0., 'S2: offset of longitudinal position [m]'],
    ['op_S2_dx', 'f', 0.05e-03, 'slit S2: horizontal size [m]'],
    ['op_S2_dy', 'f', 0.2e-03, 'slit S2: vertical size [m]'], #1.0e-03, 'slit S2: vertical size [m]'],
    ['op_S2_x', 'f', 0., 'slit S2: horizontal center position [m]'],
    ['op_S2_y', 'f', 0., 'slit S2: vertical center position [m]'],

    ['op_BPM_dz', 'f', 0., 'BPM: offset of longitudinal position [m]'],

    ['op_CRL_dz', 'f', 0., 'CRL: offset of longitudinal position [m]'],
    ['op_CRL1_fpl', 's', 'v', 'CRL1: focusing plane ("h" or "v" or "hv" or "")'],
    ['op_CRL1_delta', 'f', 4.20756805e-06, 'CRL1: refractive index decrements of material'],
    ['op_CRL1_atnl', 'f', 7312.94e-06, 'CRL1: attenuation length of material [m]'],
    ['op_CRL1_apnf', 'f', 1.e-03, 'CRL1: geometrical aparture of 1D CRL in the plane where there is no focusing'],
    ['op_CRL1_apf', 'f', 2.4e-03, 'CRL1: geometrical aparture of 1D CRL in the focusing plane'],
    ['op_CRL1_rmin', 'f', 1.5e-03, 'CRL1: radius of curface curvature at the tip of parabola [m]'],
    ['op_CRL1_n', 'i', 1, 'CRL1: number of individual lenses'],
    ['op_CRL1_thck', 'f', 80.e-06, 'CRL1: wall thickness (at the tip of parabola) [m]'],
    ['op_CRL1_x', 'f', 0., 'CRL1: horizontal center position [m]'],
    ['op_CRL1_y', 'f', 0., 'CRL1: vertical center position [m]'],

    ['op_CRL2_fpl', 's', 'v', 'CRL2: focusing plane ("h" or "v" or "hv" or "")'],
    ['op_CRL2_delta', 'f', 4.20756805e-06, 'CRL2: refractive index decrements of material'],
    ['op_CRL2_atnl', 'f', 7312.94e-06, 'CRL2: attenuation length of material [m]'],
    ['op_CRL2_apnf', 'f', 1.e-03, 'CRL2: geometrical aparture of 1D CRL in the plane where there is no focusing'],
    ['op_CRL2_apf', 'f', 1.4e-03, 'CRL2: geometrical aparture of 1D CRL in the focusing plane'],
    ['op_CRL2_rmin', 'f', 0.5e-03, 'CRL2: radius of curface curvature at the tip of parabola [m]'],
    ['op_CRL2_n', 'i', 6, 'CRL2: number of individual lenses'],
    ['op_CRL2_thck', 'f', 80.e-06, 'CRL2: wall thickness (at the tip of parabola) [m]'],
    ['op_CRL2_x', 'f', 0., 'CRL2: horizontal center position [m]'],
    ['op_CRL2_y', 'f', 0., 'CRL2: vertical center position [m]'],

    ['op_KLA_dx', 'f', 1.0e-03, 'KL aperture: horizontal size [m]'], #1.4e-03, 'KL Aperture: horizontal size [m]'],
    ['op_KLA_dy', 'f', 0.1e-03, 'KL aperture: vertical size [m]'], #0.2e-03, 'KL Aperture: vertical size [m]'],
    ['op_KL_dz', 'f', 0., 'KL: offset of longitudinal position [m]'],
    ['op_KL_fx', 'f', 3.24479, 'KL: horizontal focal length [m]'],
    ['op_KL_fy', 'f', 1.e+23, 'KL: vertical focal length [m]'],
    ['op_KL_x', 'f', 0., 'KL: horizontal center position [m]'],
    ['op_KL_y', 'f', 0., 'KL: vertical center position [m]'],

    ['op_S3_dz', 'f', 0., 'S3: offset of longitudinal position [m]'],
    ['op_S3_dx', 'f', 10.e-06, 'slit S3: horizontal size [m]'],
    ['op_S3_dy', 'f', 10.e-06, 'slit S3: vertical size [m]'],
    ['op_S3_x', 'f', 0., 'slit S3: horizontal center position [m]'],
    ['op_S3_y', 'f', 0., 'slit S3: vertical center position [m]'],

    ['op_SMP_dz', 'f', 0., 'sample: offset of longitudinal position [m]'],
    ['op_SMP_ifn', 's', 'CHX_SMP_CDI_001.pickle', 'sample: model file name (binary "dumped" SRW transmission object)'],
    ['op_SMP_ofn', 's', 'res_CHX_SMP_opt_path_dif.dat', 'sample: output file name of optical path difference data'],
    ['op_SMP_x', 'f', 0., 'sample: horizontal center position [m]'],
    ['op_SMP_y', 'f', 0., 'sample: vertical center position [m]'],

    ['op_D_dz', 'f', 0., 'detector: offset of longitudinal position [m]'],

    #to add options for different beamline cases, etc.

    #Propagation Param.:   [0][1][2][3][4] [5]  [6]  [7]  [8] [9][10][11]
    #['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 4.5, 5.0, 1.5, 2.5, 0, 0, 0], 'slit S0: propagation parameters'],
    ['op_S0_pp', 'f',      [0, 0, 1, 0, 0, 2.5, 5.0, 1.5, 2.5, 0, 0, 0], 'slit S0: propagation parameters'],
    ['op_S0_HDM_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S0 -> HDM: propagation parameters'],
    ['op_S0_S1_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S0 -> S1: propagation parameters'],
    ['op_HDM_pp', 'f',     [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror HDM: propagation parameters'],
    ['op_HDM_S1_pp', 'f',  [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift HDM -> S1: propagation parameters'],
    ['op_S1_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S1: propagation parameters'],
    ['op_S1_DCM_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> DCM: propagation parameters'],
    ['op_DCMC1_pp', 'f',   [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM Crystal #1: propagation parameters'],
    ['op_DCMC2_pp', 'f',   [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM Crystal #2: propagation parameters'],
    ['op_DCME_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'DCM Crystal #1&2: surface height error'],
    ['op_FIB_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'fiber: propagation parameters'],
    ['op_DCM_S2_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift DCM -> S2: propagation parameters'],
    ['op_S1_S2_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> S2: propagation parameters'],
    ['op_S2_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S2: propagation parameters'],
    ['op_S2_BPM_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S2 -> BPM: propagation parameters'],
    ['op_S2_CRL_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S2 -> BPM: propagation parameters'],
    ['op_BPM_CRL_pp', 'f', [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift BPM -> CRL: propagation parameters'],
    ['op_CRL1_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'CRL1: propagation parameters'],
    ['op_CRL2_pp', 'f',    [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'CRL2: propagation parameters'],
    ['op_CRL_KL_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift CRL -> KL: propagation parameters'],
    ['op_CRL_SMP_pp', 'f', [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift CRL -> sample: propagation parameters'],
    ['op_KLA_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'KL aperture: propagation parameters'],
    #['op_KL_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 5.0, 1.0, 7.0, 0, 0, 0], 'KL: propagation parameters'],
    ['op_KL_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'KL: propagation parameters'],
    ['op_KL_S3_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift KL -> S3: propagation parameters'],
    #['op_S3_pp', 'f',      [0, 0, 1, 0, 0, 0.3, 3.0, 0.3, 3.0, 0, 0, 0], 'slit S3: propagation parameters'],
    ['op_S3_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S3: propagation parameters'],
    #['op_S3_SMP_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S3 -> Sample: propagation parameters'],
    ['op_S3_SMP_pp', 'f',  [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S3 -> sample: propagation parameters'],
    ['op_SMP_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'sample: propagation parameters'],
    ['op_SMP_D_pp', 'f',   [0, 0, 1, 3, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'sample -> detector: propagation parameters'],
    #['op_fin_pp', 'f',     [0, 0, 1, 0, 1, 0.1, 5.0, 1.0, 1.5, 0, 0, 0], 'final post-propagation (resize) parameters'],
    ['op_fin_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'final post-propagation (resize) parameters'],

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

varParam = srwl_uti_ext_options(varParam)

#*********************************Entry
if __name__ == "__main__":

#---Parse options, defining Beamline elements and running calculations
    v = srwl_uti_parse_options(varParam)

#---Add some constant "parameters" (not allowed to be varied) for the beamline
    #v.und_per = 0.02 #['und_per', 'f', 0.02, 'undulator period [m]'],
    #v.und_len = 3. #['und_len', 'f', 3., 'undulator length [m]'],
    #v.und_zc = 0. #['und_zc', 'f', 0., 'undulator center longitudinal position [m]'],
    #v.und_sy = -1 #['und_sy', 'i', -1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],

#---Setup optics only if Wavefront Propagation is required:
    op = set_optics(v) if(v.ws or v.wm) else None

#---Run all requested calculations
    SRWLBeamline('Coherent Hard X-ray beamline').calc_all(v, op)
