# -*- coding: utf-8 -*-
#############################################################################
# SRWLIB Example: Virtual Beamline: a set of utilities and functions allowing to simulate
# operation of an SR Beamline.
# The standard use of this script is from command line, with some optional arguments,
# e.g. for calculation (with default parameter values) of:
# Radiation Spectrum vs Photon Energy or Power (Density) vs Time:
#    python SRWLIB_VirtBL_*.py --ss
#    python SRWLIB_VirtBL_LCLS_SXR_01.py --ss --ss_ft=t --ss_ei=-0.1e-12 --ss_ef=0.1e-12
# Input Radiation Intensity Distribution (at the first optical element):
#    python SRWLIB_VirtBL_*.py --si
# Fully-Coherent Wavefront Propagation:
#    python SRWLIB_VirtBL_*.py --ws
# Examples of ~reasonable runs at 500, 1000 and 1500 eV:
# python SRWLIB_VirtBL_LCLS_SXR_01.py --ws --w_e=500 --w_smpf=0.3 --op_fin=M3_SMP --op_S1_dy=40.e-06 --op_M1_r=1051.8 --op_fin_pp=[0,0,1,0,0,0.1,1,0.1,1,0,0,0] --op_S1_AUX_dz=0.07
# python SRWLIB_VirtBL_LCLS_SXR_01.py --ws --gbm_ave=1000 --w_e=1000 --w_rx=10.e-03 --w_ry=10.e-03 --w_smpf=0.6 --op_fin=M3_SMP --op_S1_dy=100.e-06 --op_M1_r=1051.8 --op_S1_AUX_dz=0.1 --op_M1_pp=[0,0,1,0,0,1.1,3.,1.,10.,0,0,0] --op_S1_pp=[0,0,1,0,0,1.,1.,0.1,1.,0,0,0]
# python SRWLIB_VirtBL_LCLS_SXR_01.py --ws --gbm_ave=1500 --w_e=1500 --w_rx=8.e-03 --w_ry=8.e-03 --w_smpf=0.6 --op_BL=2 --op_fin=M3_SMP --op_S1_dy=100.e-06 --op_M1_r=1051.8 --op_S1_AUX_dz=0.1 --op_M1_pp=[0,0,1,0,0,1.,3.,1.,25.,0,0,0] --op_S1_pp=[0,0,1,0,0,1.,1.,0.03,1.,0,0,0] --op_fin_pp=[0,0,1,0,1,0.2,3.,0.3,3.,0,0,0]
# For changing parameters of all these calculaitons from the default values, see the definition
# of all options in the list at the end of the script.
# v 0.02
#############################################################################

from __future__ import print_function #Python 2.7 compatibility
from srwpy.srwl_bl import *
#import time

#*********************************Setting Up Optical Elements and Propagation Parameters
def set_optics(_v):
    """This function describes optical layout of the Coherent Hoard X-ray (CHX) beamline of NSLS-II.
    Such function has to be written for every beamline to be simulated; it is specific to a particular beamline.
    :param _v: structure containing all parameters allowed to be varied for that particular beamline
    """
    
#---Instantiation of Optical Elements
    arElNamesAllOpt = [#Beamline Options
        ['M1', 'M1_G', 'G1', 'G_S1', 'S1', 'S1_AUX', 'S1_M2', 'M2', 'M2_M3', 'M3', 'M3_SMP'], #1
        ['M1', 'M1_G', 'G2', 'G_S1', 'S1', 'S1_AUX', 'S1_M2', 'M2', 'M2_M3', 'M3', 'M3_SMP'], #2
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

    #M1 (spherical mirror, mainly vertically-focusing)
    if('M1' in arElNames):
        lenM1 = 0.3; widM1 = 0.11 #Dimensions
        el.append(SRWLOptMirSph(_r=_v.op_M1_r, _size_tang=lenM1, _size_sag=widM1, _ap_shape='r',
                                _nvx=0, _nvy=cos(_v.op_M1_a), _nvz=-sin(_v.op_M1_a), _tvx=0, _tvy=sin(_v.op_M1_a), _x=_v.op_M1_x, _y=_v.op_M1_y, _treat_in_out=1))
        pp.append(_v.op_M1_pp)

        #M1 Surface Error
        horApM1 = widM1 #Projected dimensions
        verApM1 = lenM1*_v.op_M1_a
        ifnM1E = os.path.join(_v.fdir, _v.op_M1E_ifn) if len(_v.op_M1E_ifn) > 0 else ''
        if(len(ifnM1E) > 0):
            hProfDataM1E = srwl_uti_read_data_cols(ifnM1E, '\t', 0, 1)
            opM1E = srwl_opt_setup_surf_height_1d(hProfDataM1E, 'y', _ang=_v.op_M1_a, _amp_coef=_v.op_M1E_amp, _nx=200, _ny=1000, _size_x=horApM1, _size_y=verApM1, _xc=_v.op_M1E_x, _yc=_v.op_M1E_y)
            ofnM1E = os.path.join(_v.fdir, _v.op_M1E_ofn) if len(_v.op_M1E_ofn) > 0 else ''
            if(len(ofnM1E) > 0):
                pathDifM1E = opM1E.get_data(3, 3)
                srwl_uti_save_intens_ascii(pathDifM1E, opM1E.mesh, ofnM1E, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
            el.append(opM1E); pp.append(_v.op_M1E_pp)

    #M1 -> G (drift)
    if('M1_G' in arElNames): 
        el.append(SRWLOptD(zG + _v.op_G_dz - _v.op_r)); pp.append(_v.op_M1_G_pp)

    #G1 or G2 (plane VLS gratings)
    if(('G1' in arElNames) or ('G2' in arElNames)):
        #Grating Substrate (plane mirror, deflecting in vertical plane):
        GS = SRWLOptMirPl(_size_tang=0.22, _size_sag=0.05, _ap_shape='r', _nvx=0, _nvy=-cos(_v.op_G_a), _nvz=-sin(_v.op_G_a), _tvx=0, _tvy=-sin(_v.op_G_a))
        pp.append(_v.op_G_pp)

        #G1 (plane VLS grating)
        if('G1' in arElNames):
            el.append(SRWLOptG(_mirSub=GS, _m=-1, _grDen=100., _grDen1=0.02666, _grDen2=7.556e-09, _grDen3=-1.89085e-09, _grDen4=-5.04636e-13))
            #to check m (maybe =1?)
            #Calculating grating groove density coefficients from period coefficients:
            #\[Rho]0 = 1/\[Sigma]0
            #\[Rho]1 = -(\[Sigma]1/\[Sigma]0^2)
            #\[Rho]2 = (\[Sigma]1^2 - \[Sigma]0 \[Sigma]2)/\[Sigma]0^3
            #\[Rho]3 = (-\[Sigma]1^3 + 2 \[Sigma]0 \[Sigma]1 \[Sigma]2 - \[Sigma]0^2 \[Sigma]3)/\[Sigma]0^4
            #\[Rho]4 = (\[Sigma]1^4 - 3 \[Sigma]0 \[Sigma]1^2 \[Sigma]2 + \[Sigma]0^2 \[Sigma]2^2 + 2 \[Sigma]0^2 \[Sigma]1 \[Sigma]3)/\[Sigma]0^5
        
        #G2 (plane VLS grating)
        if('G2' in arElNames):
            el.append(SRWLOptG(_mirSub=GS, _m=-1, _grDen=200., _grDen1=0.05332, _grDen2=2.15112e-07, _grDen3=-3.67505e-09, _grDen4=-9.94826e-13))
            #to check m (maybe =1?)

    #G -> S1 (drift)
    if('G_S1' in arElNames): 
        el.append(SRWLOptD(zS1 + _v.op_S1_dz - zG - _v.op_G_dz)); pp.append(_v.op_G_S1_pp)

    #S1 (slit)
    if('S1' in arElNames): 
        el.append(SRWLOptA('r', 'a', _v.op_S1_dx, _v.op_S1_dy, _v.op_S1_x, _v.op_S1_y)); pp.append(_v.op_S1_pp)

    #S1 -> AUX (drift)
    if('S1_AUX' in arElNames):
        if(_v.op_S1_AUX_dz > 0):
            el.append(SRWLOptD(_v.op_S1_AUX_dz)); pp.append(_v.op_S1_AUX_pp)

    #S1 -> M2 (drift)
    if('S1_M2' in arElNames): 
        el.append(SRWLOptD(zM2 + _v.op_M2_dz - zS1 - _v.op_S1_dz - _v.op_S1_AUX_dz)); pp.append(_v.op_S1_M2_pp)

    #M2 (horizontally-focusing elliptical mirror)
    if('M2' in arElNames): 
        lenM2 = 0.4; widM2 = 0.025 #Dimensions
        el.append(SRWLOptMirEl(_p=_v.op_M2_p, _q=_v.op_M2_q, _ang_graz=_v.op_M2_a, _size_tang=lenM2, _size_sag=widM2, _ap_shape='r',
                               _nvx=-cos(_v.op_M2_a), _nvy=0, _nvz=-sin(_v.op_M2_a), _tvx=-sin(_v.op_M2_a), _tvy=0, _x=_v.op_M2_x, _y=_v.op_M2_y, _treat_in_out=1)) #To check
                               #_nvx=cos(_v.op_M2_a), _nvy=0, _nvz=-sin(_v.op_M2_a), _tvx=-sin(_v.op_M2_a), _tvy=0, _x=_v.op_M2_x, _y=_v.op_M2_y, _treat_in_out=1))
        pp.append(_v.op_M2_pp)

        #M2 Surface Error
        horApM2 = lenM2*_v.op_M2_a #Projected dimensions
        verApM2 = widM2
        ifnM2E = os.path.join(_v.fdir, _v.op_M2E_ifn) if len(_v.op_M2E_ifn) > 0 else ''
        if(len(ifnM2E) > 0):
            hProfDataM2E = srwl_uti_read_data_cols(ifnM2E, '\t', 0, 1)
            opM2E = srwl_opt_setup_surf_height_1d(hProfDataM2E, 'x', _ang=_v.op_M2_a, _amp_coef=_v.op_M2E_amp, _nx=1000, _ny=200, _size_x=horApM2, _size_y=verApM2, _xc=_v.op_M2E_x, _yc=_v.op_M2E_y)
            ofnM2E = os.path.join(_v.fdir, _v.op_M2E_ofn) if len(_v.op_M2E_ofn) > 0 else ''
            if(len(ofnM2E) > 0):
                pathDifM2E = opM2E.get_data(3, 3)
                srwl_uti_save_intens_ascii(pathDifM2E, opM2E.mesh, ofnM2E, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
            el.append(opM2E); pp.append(_v.op_M2E_pp)

    #M2 -> M3 (drift)
    if('M2_M3' in arElNames): 
        el.append(SRWLOptD(zM3 + _v.op_M3_dz - zM2 - _v.op_M2_dz)); pp.append(_v.op_M2_M3_pp)

    #M3 (vertically-focusing elliptical mirror)
    if('M3' in arElNames): 
        lenM3 = 0.4; widM3 = 0.025 #Dimensions
        el.append(SRWLOptMirEl(_p=_v.op_M3_p, _q=_v.op_M3_q, _ang_graz=_v.op_M3_a, _size_tang=lenM3, _size_sag=widM3, _ap_shape='r',
                               _nvx=0, _nvy=cos(_v.op_M3_a), _nvz=-sin(_v.op_M3_a), _tvx=0, _tvy=sin(_v.op_M3_a), _x=_v.op_M3_x, _y=_v.op_M3_y, _treat_in_out=1))
        pp.append(_v.op_M3_pp)

        #M3 Surface Error
        horApM3 = widM3 #Projected dimensions
        verApM3 = lenM3*_v.op_M3_a
        ifnM3E = os.path.join(_v.fdir, _v.op_M3E_ifn) if len(_v.op_M3E_ifn) > 0 else ''
        if(len(ifnM3E) > 0):
            hProfDataM3E = srwl_uti_read_data_cols(ifnM3E, '\t', 0, 1)
            opM3E = srwl_opt_setup_surf_height_1d(hProfDataM3E, 'y', _ang=_v.op_M3_a, _amp_coef=_v.op_M3E_amp, _nx=200, _ny=1000, _size_x=horApM3, _size_y=verApM3, _xc=_v.op_M3E_x, _yc=_v.op_M3E_y)
            ofnM3E = os.path.join(_v.fdir, _v.op_M3E_ofn) if len(_v.op_M3E_ofn) > 0 else ''
            if(len(ofnM3E) > 0):
                pathDifM3E = opM3E.get_data(3, 3)
                srwl_uti_save_intens_ascii(pathDifM3E, opM3E.mesh, ofnM3E, 0, ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Dif.'], _arUnits=['', 'm', 'm', 'm'])
            el.append(opM3E); pp.append(_v.op_M3E_pp)

    #M3 -> SMP (drift)
    if('M3_SMP' in arElNames): 
        el.append(SRWLOptD(zSMP + _v.op_SMP_dz - zM3 - _v.op_M3_dz)); pp.append(_v.op_M3_SMP_pp)

    pp.append(_v.op_fin_pp)

    return SRWLOptC(el, pp)

#*********************************Parameters allowed to be varied
#---Nominal Positions of Optical Elements [m] with respect to source (used as default values in the varParam list and in set_optics function)
zM1 = 125.1 #M1 (spherical mirror)
zG = 125.4 #G1/G2 (VLS gratings)
zS1 = 132.9 #S1 (exit slit of mono)
zM2 = 137.4 #M2 (vertically-focusing elliptical mirror)
zM3 = 137.9 #M3 (horizontally-focusing elliptical mirror)
zSMP = 139.4 #Endstation (sample position?)

#---List of supported options / commands / parameters allowed to be varied for this Beamline (comment-out unnecessary):   
varParam = [
#---Data Folder
    ['fdir', 's', os.path.join(os.getcwd(), 'data_LCLS_SXR'), 'folder (directory) name for reading-in input and saving output data files'],

#---Gaussian Beam
    ['gbm_pen', 'f', 0.001, 'pulse energy [J]'],
    ['gbm_rep', 'f', 1, 'rep. rate [Hz]'],
    ['gbm_pol', 'f', 1, 'polarization: 1- lin. hor., 2- lin. vert., 3- lin. 45 deg., 4- lin.135 deg., 5- circ. right, 6- circ. left'],
    ['gbm_ave', 'f', 500, 'average photon energy [eV]'],
    ['gbm_x', 'f', 0., 'average horizontal coordinates of waist [m]'],
    ['gbm_y', 'f', 0., 'average vertical coordinates of waist [m]'],
    ['gbm_xp', 'f', 0., 'average horizontal angle at waist [rad]'],
    ['gbm_yp', 'f', 0., 'average verical angle at waist [rad]'],
    ['gbm_z', 'f', 0., 'average longitudinal coordinate of waist [m]'],
    ['gbm_sx', 'f', 10.e-06, 'RMS beam size vs horizontal position [m] at waist (for intensity)'],
    ['gbm_sy', 'f', 10.e-06, 'RMS beam size vs vertical position [m] at waist (for intensity)'],
    ['gbm_st', 'f', 10.e-15, 'RMS pulse duration [s] (for intensity)'],
    ['gbm_mx', 'f', 0., 'transverse Gauss-Hermite mode order in horizontal direction'],
    ['gbm_my', 'f', 0., 'transverse Gauss-Hermite mode order in vertical direction'],
    ['gbm_ca', 's', 'c', 'treat gbm_sx, gbm_sy as sizes in [m] in coordinate representation (="c") or as angular divergences in [rad] in angular representation (="a")'],
    ['gbm_ft', 's', 't', 'treat gbm_st as pulse duration in [s] in time domain/representation (="t") or as bandwidth in [eV] in frequency domain/representation (="f")'],

#---SASE parameters (for Genesis of other code) - to be added eventually

#---Calculation Types (default parameters specific to this beamline)
#Spectrum vs Photon Energy
    ['ss_ei', 'f', 499., 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 501., 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 200, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_u', 'i', '2', 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    
#General Wavefront parameters (used at several different calculations)
    ['w_e', 'f', 500., 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_rx', 'f', 20.e-03, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_ry', 'f', 20.e-03, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_u', 'i', '2', 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    
#---Beamline Optics
    ['op_r', 'f', zM1, 'longitudinal position of the first optical element [m]'],
    ['op_fin', 's', 'M3_SMP', 'name of the final optical element wavefront has to be propagated through'],

    ['op_BL', 'f', 1, 'beamline version/option number'],

    ['op_M1_r', 'f', 1049., 'M1: radius of curvature [m]'],
    ['op_M1_a', 'f', 0.0139626, 'M1: grazing angle [rad]'],
    ['op_M1_x', 'f', 0., 'M1: horizontal center position [m]'],
    ['op_M1_y', 'f', 0., 'M1: vertical center position [m]'],

    ['op_M1E_ifn', 's', '', 'M1: input file name of height profile data'],
    #['op_M1E_ifn', 's', 'CHX_HDM_height_prof_1d.dat', 'mirror HDM: input file name of height profile data'],
    ['op_M1E_amp', 'f', 1., 'M1: amplification coefficient for height profile data'],
    ['op_M1E_ofn', 's', 'res_M1_opt_path_dif.dat', 'M1: output file name of optical path difference data'],
    ['op_M1E_x', 'f', 0., 'M1: horizontal center position for height error [m]'],
    ['op_M1E_y', 'f', 0., 'M1: vertical center position for height error [m]'],

    ['op_G_dz', 'f', 0., 'G1(G2): offset of longitudinal position [m]'],
    ['op_G_a', 'f', 0.0251327, 'G1(G2): grazing angle [rad]'],
    ['op_G_x', 'f', 0., 'G1(G2): horizontal center position [m]'],
    ['op_G_y', 'f', 0., 'G1(G2): vertical center position [m]'],

    ['op_S1_dz', 'f', 0., 'S1: offset of longitudinal position [m]'],
    ['op_S1_dx', 'f', 20.e-03, 'slit S1: horizontal size [m]'],
    ['op_S1_dy', 'f', 0.1e-03, 'slit S1: vertical size [m]'],
    ['op_S1_x', 'f', 0., 'slit S1: horizontal center position [m]'],
    ['op_S1_y', 'f', 0., 'slit S1: vertical center position [m]'],

    ['op_S1_AUX_dz', 'f', 0.2, 'AUX: auxiliary small drift after S1 [m]'],

    ['op_M2_dz', 'f', 0., 'M2: offset of longitudinal position [m]'],
    ['op_M2_p', 'f', zM2, 'M2: p-parameter (design distance to source) [m]'],
    ['op_M2_q', 'f', zSMP - zM2, 'M2: q-parameter (design distance to image) [m]'],
    ['op_M2_a', 'f', 0.0139626, 'M2: grazing angle [rad]'],
    ['op_M2_x', 'f', 0., 'M2: horizontal center position [m]'],
    ['op_M2_y', 'f', 0., 'M2: vertical center position [m]'],

    ['op_M2E_ifn', 's', '', 'M2: input file name of height profile data'],
    ['op_M2E_amp', 'f', 1., 'M2: amplification coefficient for height profile data'],
    ['op_M2E_ofn', 's', 'res_M2_opt_path_dif.dat', 'M2: output file name of optical path difference data'],
    ['op_M2E_x', 'f', 0., 'M2: horizontal center position for height error [m]'],
    ['op_M2E_y', 'f', 0., 'M2: vertical center position for height error [m]'],

    ['op_M3_dz', 'f', 0., 'M3: offset of longitudinal position [m]'],
    ['op_M3_p', 'f', zM3 - zS1, 'M3: p-parameter (design distance to source) [m]'],
    ['op_M3_q', 'f', zSMP - zM3, 'M3: q-parameter (design distance to image) [m]'],
    ['op_M3_a', 'f', 0.0139626, 'M3: grazing angle [rad]'],
    ['op_M3_x', 'f', 0., 'M3: horizontal center position [m]'],
    ['op_M3_y', 'f', 0., 'M3: vertical center position [m]'],

    ['op_M3E_ifn', 's', '', 'M3: input file name of height profile data'],
    ['op_M3E_amp', 'f', 1., 'M3: amplification coefficient for height profile data'],
    ['op_M3E_ofn', 's', 'res_M3_opt_path_dif.dat', 'M3: output file name of optical path difference data'],
    ['op_M3E_x', 'f', 0., 'M3: horizontal center position for height error [m]'],
    ['op_M3E_y', 'f', 0., 'M3: vertical center position for height error [m]'],
    
    ['op_SMP_dz', 'f', 0., 'sample: offset of longitudinal position [m]'],

    #to add options when/if necessary

    #Propagation Params:   [0][1][2][3][4] [5]  [6]  [7]  [8] [9][10][11]
    ['op_M1_pp', 'f',      [0, 0, 1, 0, 0, 1.5, 3.0, 4.5, 2.0, 0, 0, 0], 'mirror M1: propagation parameters; note: it can include non-default orientation of output frame in fields [12]-[16]'],
    ['op_M1E_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror M1 height error: propagation parameters'],
    ['op_M1_G_pp', 'f',    [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift M1 -> G: propagation parameters'],
    ['op_G_pp', 'f',       [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'grating G1 or G2: propagation parameters; note: it can include non-default orientation of output frame in fields [12]-[16]'],
    ['op_G_S1_pp', 'f',    [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift G1(G2) -> S1: propagation parameters'],
    ['op_S1_pp', 'f',      [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'slit S1: propagation parameters'],
    ['op_S1_AUX_pp', 'f',  [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> Aux position: propagation parameters'], #Auxiliary shift over a small distance (applied because the propagator with semi-analytical treatment of the quad. phae term can't be used at propagation from waist)
    ['op_S1_M2_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift S1 -> M2: propagation parameters'],
    ['op_M2_pp', 'f',      [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror M2: propagation parameters; note: it can include non-default orientation of output frame in fields [12]-[16]'],
    ['op_M2E_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror M2 height error: propagation parameters'],
    ['op_M2_M3_pp', 'f',   [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift M2 -> M3: propagation parameters'],
    ['op_M3_pp', 'f',      [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror M3: propagation parameters; note: it can include non-default orientation of output frame in fields [12]-[16]'],
    ['op_M3E_pp', 'f',     [0, 0, 1, 0, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'mirror M3 height error: propagation parameters'],
    ['op_M3_SMP_pp', 'f',  [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0], 'drift M3 -> Sample: propagation parameters'],
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

varParam = srwl_uti_ext_options(varParam) #Adding other default options
    
#*********************************Entry
if __name__ == "__main__":

#---Parse options, defining Beamline elements and running calculations
    v = srwl_uti_parse_options(varParam)
    
#---Setup optics only if Wavefront Propagation is required:
    op = set_optics(v) if(v.ws or v.wm) else None

#---Run all requested calculations
    SRWLBeamline('SXR at LCLS').calc_all(v, op)
