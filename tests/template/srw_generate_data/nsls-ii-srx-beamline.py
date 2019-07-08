#!/usr/bin/env python
import os
try:
    __IPYTHON__
    import sys
    del sys.argv[1:]
except:
    pass


import srwl_bl
import srwlib
import srwlpy
import srwl_uti_smp


def set_optics(v=None):
    el = []
    pp = []
    names = ['S0', 'S0_HFM', 'HFM', 'HFM_S1', 'S1', 'S1_DCM_C1', 'DCM_C1', 'DCM_C2', 'DCM_C2_At_BPM1', 'At_BPM1', 'At_BPM1_Before_SSA', 'Before_SSA', 'SSA', 'SSA_AKB', 'AKB', 'AKB_KBV', 'KBV', 'KBV_KBH', 'KBH', 'KBH_At_Sample', 'At_Sample']
    for el_name in names:
        if el_name == 'S0':
            # S0: aperture 33.1798m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_S0_shape,
                _ap_or_ob='a',
                _Dx=v.op_S0_Dx,
                _Dy=v.op_S0_Dy,
                _x=v.op_S0_x,
                _y=v.op_S0_y,
            ))
            pp.append(v.op_S0_pp)
        elif el_name == 'S0_HFM':
            # S0_HFM: drift 33.1798m
            el.append(srwlib.SRWLOptD(
                _L=v.op_S0_HFM_L,
            ))
            pp.append(v.op_S0_HFM_pp)
        elif el_name == 'HFM':
            # HFM: sphericalMirror 34.2608m
            el.append(srwlib.SRWLOptMirSph(
                _r=v.op_HFM_r,
                _size_tang=v.op_HFM_size_tang,
                _size_sag=v.op_HFM_size_sag,
                _nvx=v.op_HFM_nvx,
                _nvy=v.op_HFM_nvy,
                _nvz=v.op_HFM_nvz,
                _tvx=v.op_HFM_tvx,
                _tvy=v.op_HFM_tvy,
                _x=v.op_HFM_x,
                _y=v.op_HFM_y,
            ))
            pp.append(v.op_HFM_pp)
            
        elif el_name == 'HFM_S1':
            # HFM_S1: drift 34.2608m
            el.append(srwlib.SRWLOptD(
                _L=v.op_HFM_S1_L,
            ))
            pp.append(v.op_HFM_S1_pp)
        elif el_name == 'S1':
            # S1: aperture 35.6678m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_S1_shape,
                _ap_or_ob='a',
                _Dx=v.op_S1_Dx,
                _Dy=v.op_S1_Dy,
                _x=v.op_S1_x,
                _y=v.op_S1_y,
            ))
            pp.append(v.op_S1_pp)
        elif el_name == 'S1_DCM_C1':
            # S1_DCM_C1: drift 35.6678m
            el.append(srwlib.SRWLOptD(
                _L=v.op_S1_DCM_C1_L,
            ))
            pp.append(v.op_S1_DCM_C1_pp)
        elif el_name == 'DCM_C1':
            # DCM_C1: crystal 36.4488m
            crystal = srwlib.SRWLOptCryst(
                _d_sp=v.op_DCM_C1_d_sp,
                _psi0r=v.op_DCM_C1_psi0r,
                _psi0i=v.op_DCM_C1_psi0i,
                _psi_hr=v.op_DCM_C1_psiHr,
                _psi_hi=v.op_DCM_C1_psiHi,
                _psi_hbr=v.op_DCM_C1_psiHBr,
                _psi_hbi=v.op_DCM_C1_psiHBi,
                _tc=v.op_DCM_C1_tc,
                _ang_as=v.op_DCM_C1_ang_as,
            )
            crystal.set_orient(
                _nvx=v.op_DCM_C1_nvx,
                _nvy=v.op_DCM_C1_nvy,
                _nvz=v.op_DCM_C1_nvz,
                _tvx=v.op_DCM_C1_tvx,
                _tvy=v.op_DCM_C1_tvy,
            )
            el.append(crystal)
            pp.append(v.op_DCM_C1_pp)
            
        elif el_name == 'DCM_C2':
            # DCM_C2: crystal 36.4488m
            crystal = srwlib.SRWLOptCryst(
                _d_sp=v.op_DCM_C2_d_sp,
                _psi0r=v.op_DCM_C2_psi0r,
                _psi0i=v.op_DCM_C2_psi0i,
                _psi_hr=v.op_DCM_C2_psiHr,
                _psi_hi=v.op_DCM_C2_psiHi,
                _psi_hbr=v.op_DCM_C2_psiHBr,
                _psi_hbi=v.op_DCM_C2_psiHBi,
                _tc=v.op_DCM_C2_tc,
                _ang_as=v.op_DCM_C2_ang_as,
            )
            crystal.set_orient(
                _nvx=v.op_DCM_C2_nvx,
                _nvy=v.op_DCM_C2_nvy,
                _nvz=v.op_DCM_C2_nvz,
                _tvx=v.op_DCM_C2_tvx,
                _tvy=v.op_DCM_C2_tvy,
            )
            el.append(crystal)
            pp.append(v.op_DCM_C2_pp)
            
        elif el_name == 'DCM_C2_At_BPM1':
            # DCM_C2_At_BPM1: drift 36.4488m
            el.append(srwlib.SRWLOptD(
                _L=v.op_DCM_C2_At_BPM1_L,
            ))
            pp.append(v.op_DCM_C2_At_BPM1_pp)
        elif el_name == 'At_BPM1':
            # At_BPM1: watch 38.6904m
            pass
        elif el_name == 'At_BPM1_Before_SSA':
            # At_BPM1_Before_SSA: drift 38.6904m
            el.append(srwlib.SRWLOptD(
                _L=v.op_At_BPM1_Before_SSA_L,
            ))
            pp.append(v.op_At_BPM1_Before_SSA_pp)
        elif el_name == 'Before_SSA':
            # Before_SSA: watch 50.6572m
            pass
        elif el_name == 'SSA':
            # SSA: aperture 50.6572m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_SSA_shape,
                _ap_or_ob='a',
                _Dx=v.op_SSA_Dx,
                _Dy=v.op_SSA_Dy,
                _x=v.op_SSA_x,
                _y=v.op_SSA_y,
            ))
            pp.append(v.op_SSA_pp)
        elif el_name == 'SSA_AKB':
            # SSA_AKB: drift 50.6572m
            el.append(srwlib.SRWLOptD(
                _L=v.op_SSA_AKB_L,
            ))
            pp.append(v.op_SSA_AKB_pp)
        elif el_name == 'AKB':
            # AKB: aperture 62.488m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_AKB_shape,
                _ap_or_ob='a',
                _Dx=v.op_AKB_Dx,
                _Dy=v.op_AKB_Dy,
                _x=v.op_AKB_x,
                _y=v.op_AKB_y,
            ))
            pp.append(v.op_AKB_pp)
        elif el_name == 'AKB_KBV':
            # AKB_KBV: drift 62.488m
            el.append(srwlib.SRWLOptD(
                _L=v.op_AKB_KBV_L,
            ))
            pp.append(v.op_AKB_KBV_pp)
        elif el_name == 'KBV':
            # KBV: ellipsoidMirror 62.663m
            el.append(srwlib.SRWLOptMirEl(
                _p=v.op_KBV_p,
                _q=v.op_KBV_q,
                _ang_graz=v.op_KBV_ang,
                _size_tang=v.op_KBV_size_tang,
                _size_sag=v.op_KBV_size_sag,
                _nvx=v.op_KBV_nvx,
                _nvy=v.op_KBV_nvy,
                _nvz=v.op_KBV_nvz,
                _tvx=v.op_KBV_tvx,
                _tvy=v.op_KBV_tvy,
                _x=v.op_KBV_x,
                _y=v.op_KBV_y,
            ))
            pp.append(v.op_KBV_pp)
            
        elif el_name == 'KBV_KBH':
            # KBV_KBH: drift 62.663m
            el.append(srwlib.SRWLOptD(
                _L=v.op_KBV_KBH_L,
            ))
            pp.append(v.op_KBV_KBH_pp)
        elif el_name == 'KBH':
            # KBH: ellipsoidMirror 63.0m
            el.append(srwlib.SRWLOptMirEl(
                _p=v.op_KBH_p,
                _q=v.op_KBH_q,
                _ang_graz=v.op_KBH_ang,
                _size_tang=v.op_KBH_size_tang,
                _size_sag=v.op_KBH_size_sag,
                _nvx=v.op_KBH_nvx,
                _nvy=v.op_KBH_nvy,
                _nvz=v.op_KBH_nvz,
                _tvx=v.op_KBH_tvx,
                _tvy=v.op_KBH_tvy,
                _x=v.op_KBH_x,
                _y=v.op_KBH_y,
            ))
            pp.append(v.op_KBH_pp)
            
        elif el_name == 'KBH_At_Sample':
            # KBH_At_Sample: drift 63.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_KBH_At_Sample_L,
            ))
            pp.append(v.op_KBH_At_Sample_pp)
        elif el_name == 'At_Sample':
            # At_Sample: watch 63.3m
            pass
    pp.append(v.op_fin_pp)
    return srwlib.SRWLOptC(el, pp)


varParam = srwl_bl.srwl_uti_ext_options([
    ['name', 's', 'NSLS-II SRX beamline', 'simulation name'],

#---Data Folder
    ['fdir', 's', '', 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', 'NSLS-II Low Beta Day 1', 'standard electron beam name'],
    ['ebm_nms', 's', '', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', 0.5, 'electron beam current [A]'],
    ['ebm_e', 'f', 3.0, 'electron beam avarage energy [GeV]'],
    ['ebm_de', 'f', 0.0, 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', 0.0, 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', 0.0, 'electron beam initial average vertical position [m]'],
    ['ebm_xp', 'f', 0.0, 'electron beam initial average horizontal angle [rad]'],
    ['ebm_yp', 'f', 0.0, 'electron beam initial average vertical angle [rad]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', 0.0, 'electron beam longitudinal drift [m] to be performed before a required calculation'],
    ['ebm_ens', 'f', 0.00089, 'electron beam relative energy spread'],
    ['ebm_emx', 'f', 9e-10, 'electron beam horizontal emittance [m]'],
    ['ebm_emy', 'f', 8e-12, 'electron beam vertical emittance [m]'],
    # Definition of the beam through Twiss:
    ['ebm_betax', 'f', 1.84, 'horizontal beta-function [m]'],
    ['ebm_betay', 'f', 1.17, 'vertical beta-function [m]'],
    ['ebm_alphax', 'f', 0.0, 'horizontal alpha-function [rad]'],
    ['ebm_alphay', 'f', 0.0, 'vertical alpha-function [rad]'],
    ['ebm_etax', 'f', 0.0, 'horizontal dispersion function [m]'],
    ['ebm_etay', 'f', 0.0, 'vertical dispersion function [m]'],
    ['ebm_etaxp', 'f', 0.0, 'horizontal dispersion function derivative [rad]'],
    ['ebm_etayp', 'f', 0.0, 'vertical dispersion function derivative [rad]'],
    # Definition of the beam through Moments:
    ['ebm_sigx', 'f', 4.06939799e-05, 'horizontal RMS size of electron beam [m]'],
    ['ebm_sigy', 'f', 3.05941171e-06, 'vertical RMS size of electron beam [m]'],
    ['ebm_sigxp', 'f', 2.211629342e-05, 'horizontal RMS angular divergence of electron beam [rad]'],
    ['ebm_sigyp', 'f', 2.6148818e-06, 'vertical RMS angular divergence of electron beam [rad]'],
    ['ebm_mxxp', 'f', 0.0, 'horizontal position-angle mixed 2nd order moment of electron beam [m]'],
    ['ebm_myyp', 'f', 0.0, 'vertical position-angle mixed 2nd order moment of electron beam [m]'],

#---Undulator
    ['und_bx', 'f', 0.0, 'undulator horizontal peak magnetic field [T]'],
    ['und_by', 'f', 0.88770981, 'undulator vertical peak magnetic field [T]'],
    ['und_phx', 'f', 0.0, 'initial phase of the horizontal magnetic field [rad]'],
    ['und_phy', 'f', 0.0, 'initial phase of the vertical magnetic field [rad]'],
    ['und_b2e', '', '', 'estimate undulator fundamental photon energy (in [eV]) for the amplitude of sinusoidal magnetic field defined by und_b or und_bx, und_by', 'store_true'],
    ['und_e2b', '', '', 'estimate undulator field amplitude (in [T]) for the photon energy defined by w_e', 'store_true'],
    ['und_per', 'f', 0.02, 'undulator period [m]'],
    ['und_len', 'f', 3.0, 'undulator length [m]'],
    ['und_zc', 'f', -1.25, 'undulator center longitudinal position [m]'],
    ['und_sx', 'i', 1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    ['und_sy', 'i', -1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    ['und_g', 'f', 6.715, 'undulator gap [mm] (assumes availability of magnetic measurement or simulation data)'],
    ['und_ph', 'f', 0.0, 'shift of magnet arrays [mm] for which the field should be set up'],
    ['und_mdir', 's', '', 'name of magnetic measurements sub-folder'],
    ['und_mfs', 's', '', 'name of magnetic measurements for different gaps summary file'],



#---Calculation Types
    # Electron Trajectory
    ['tr', '', '', 'calculate electron trajectory', 'store_true'],
    ['tr_cti', 'f', 0.0, 'initial time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_ctf', 'f', 0.0, 'final time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_np', 'f', 10000, 'number of points for trajectory calculation'],
    ['tr_mag', 'i', 2, 'magnetic field to be used for trajectory calculation: 1- approximate, 2- accurate'],
    ['tr_fn', 's', 'res_trj.dat', 'file name for saving calculated trajectory data'],
    ['tr_pl', 's', '', 'plot the resulting trajectiry in graph(s): ""- dont plot, otherwise the string should list the trajectory components to plot'],

    #Single-Electron Spectrum vs Photon Energy
    ['ss', '', '', 'calculate single-e spectrum vs photon energy', 'store_true'],
    ['ss_ei', 'f', 100.0, 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 20000.0, 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 10000, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_x', 'f', 0.0, 'horizontal position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_y', 'f', 0.0, 'vertical position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_meth', 'i', 1, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['ss_prec', 'f', 0.01, 'relative precision for single-e spectrum vs photon energy calculation (nominal value is 0.01)'],
    ['ss_pol', 'i', 6, 'polarization component to extract after spectrum vs photon energy calculation: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['ss_mag', 'i', 2, 'magnetic field to be used for single-e spectrum vs photon energy calculation: 1- approximate, 2- accurate'],
    ['ss_ft', 's', 'f', 'presentation/domain: "f"- frequency (photon energy), "t"- time'],
    ['ss_u', 'i', 1, 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    ['ss_fn', 's', 'res_spec_se.dat', 'file name for saving calculated single-e spectrum vs photon energy'],
    ['ss_pl', 's', '', 'plot the resulting single-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],

    #Multi-Electron Spectrum vs Photon Energy (taking into account e-beam emittance, energy spread and collection aperture size)
    ['sm', '', '', 'calculate multi-e spectrum vs photon energy', 'store_true'],
    ['sm_ei', 'f', 100.0, 'initial photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ef', 'f', 20000.0, 'final photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ne', 'i', 10000, 'number of points vs photon energy for multi-e spectrum vs photon energy calculation'],
    ['sm_x', 'f', 0.0, 'horizontal center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_rx', 'f', 0.001, 'range of horizontal position / horizontal aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_nx', 'i', 1, 'number of points vs horizontal position for multi-e spectrum vs photon energy calculation'],
    ['sm_y', 'f', 0.0, 'vertical center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ry', 'f', 0.001, 'range of vertical position / vertical aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ny', 'i', 1, 'number of points vs vertical position for multi-e spectrum vs photon energy calculation'],
    ['sm_mag', 'i', 1, 'magnetic field to be used for calculation of multi-e spectrum spectrum or intensity distribution: 1- approximate, 2- accurate'],
    ['sm_hi', 'i', 1, 'initial UR spectral harmonic to be taken into account for multi-e spectrum vs photon energy calculation'],
    ['sm_hf', 'i', 15, 'final UR spectral harmonic to be taken into account for multi-e spectrum vs photon energy calculation'],
    ['sm_prl', 'f', 1.0, 'longitudinal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_pra', 'f', 1.0, 'azimuthal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_meth', 'i', -1, 'method to use for spectrum vs photon energy calculation in case of arbitrary input magnetic field: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler", -1- dont use this accurate integration method (rather use approximate if possible)'],
    ['sm_prec', 'f', 0.01, 'relative precision for spectrum vs photon energy calculation in case of arbitrary input magnetic field (nominal value is 0.01)'],
    ['sm_nm', 'i', 1, 'number of macro-electrons for calculation of spectrum in case of arbitrary input magnetic field'],
    ['sm_na', 'i', 5, 'number of macro-electrons to average on each node at parallel (MPI-based) calculation of spectrum in case of arbitrary input magnetic field'],
    ['sm_ns', 'i', 5, 'saving periodicity (in terms of macro-electrons) for intermediate intensity at calculation of multi-electron spectrum in case of arbitrary input magnetic field'],
    ['sm_type', 'i', 1, 'calculate flux (=1) or flux per unit surface (=2)'],
    ['sm_pol', 'i', 6, 'polarization component to extract after calculation of multi-e flux or intensity: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['sm_rm', 'i', 1, 'method for generation of pseudo-random numbers for e-beam phase-space integration: 1- standard pseudo-random number generator, 2- Halton sequences, 3- LPtau sequences (to be implemented)'],
    ['sm_fn', 's', 'res_spec_me.dat', 'file name for saving calculated milti-e spectrum vs photon energy'],
    ['sm_pl', 's', '', 'plot the resulting spectrum-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],
    #to add options for the multi-e calculation from "accurate" magnetic field

    #Power Density Distribution vs horizontal and vertical position
    ['pw', '', '', 'calculate SR power density distribution', 'store_true'],
    ['pw_x', 'f', 0.0, 'central horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_rx', 'f', 0.025, 'range of horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_nx', 'i', 100, 'number of points vs horizontal position for calculation of power density distribution'],
    ['pw_y', 'f', 0.0, 'central vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ry', 'f', 0.025, 'range of vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ny', 'i', 100, 'number of points vs vertical position for calculation of power density distribution'],
    ['pw_pr', 'f', 1.0, 'precision factor for calculation of power density distribution'],
    ['pw_meth', 'i', 1, 'power density computation method (1- "near field", 2- "far field")'],
    ['pw_zst', 'f', 0., 'initial longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_zfi', 'f', 0., 'final longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_mag', 'i', 2, 'magnetic field to be used for power density calculation: 1- approximate, 2- accurate'],
    ['pw_fn', 's', 'res_pow.dat', 'file name for saving calculated power density distribution'],
    ['pw_pl', 's', '', 'plot the resulting power density distribution in a graph: ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    #Single-Electron Intensity distribution vs horizontal and vertical position
    ['si', '', '', 'calculate single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position', 'store_true'],
    #Single-Electron Wavefront Propagation
    ['ws', '', '', 'calculate single-electron (/ fully coherent) wavefront propagation', 'store_true'],
    #Multi-Electron (partially-coherent) Wavefront Propagation
    ['wm', '', '', 'calculate multi-electron (/ partially coherent) wavefront propagation', 'store_true'],

    ['w_e', 'f', 8000.0, 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1.0, 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', 0.0, 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', 0.0025, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 100, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', 0.0, 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', 0.0013, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 100, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', 0.1, 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', 1, 'method to use for calculation of intensity distribution vs horizontal and vertical position: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['w_prec', 'f', 0.01, 'relative precision for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_u', 'i', 1, 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    ['si_pol', 'i', 6, 'polarization component to extract after calculation of intensity distribution: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['si_type', 'i', 0, 'type of a characteristic to be extracted after calculation of intensity distribution: 0- Single-Electron Intensity, 1- Multi-Electron Intensity, 2- Single-Electron Flux, 3- Multi-Electron Flux, 4- Single-Electron Radiation Phase, 5- Re(E): Real part of Single-Electron Electric Field, 6- Im(E): Imaginary part of Single-Electron Electric Field, 7- Single-Electron Intensity, integrated over Time or Photon Energy'],
    ['w_mag', 'i', 2, 'magnetic field to be used for calculation of intensity distribution vs horizontal and vertical position: 1- approximate, 2- accurate'],

    ['si_fn', 's', 'res_int_se.dat', 'file name for saving calculated single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position'],
    ['si_pl', 's', '', 'plot the input intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],
    ['ws_fni', 's', 'res_int_pr_se.dat', 'file name for saving propagated single-e intensity distribution vs horizontal and vertical position'],
    ['ws_pl', 's', '', 'plot the resulting intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    ['wm_nm', 'i', 100000, 'number of macro-electrons (coherent wavefronts) for calculation of multi-electron wavefront propagation'],
    ['wm_na', 'i', 5, 'number of macro-electrons (coherent wavefronts) to average on each node for parallel (MPI-based) calculation of multi-electron wavefront propagation'],
    ['wm_ns', 'i', 5, 'saving periodicity (in terms of macro-electrons / coherent wavefronts) for intermediate intensity at multi-electron wavefront propagation calculation'],
    ['wm_ch', 'i', 0, 'type of a characteristic to be extracted after calculation of multi-electron wavefront propagation: #0- intensity (s0); 1- four Stokes components; 2- mutual intensity cut vs x; 3- mutual intensity cut vs y; 40- intensity(s0), mutual intensity cuts and degree of coherence vs X & Y'],
    ['wm_ap', 'i', 0, 'switch specifying representation of the resulting Stokes parameters: coordinate (0) or angular (1)'],
    ['wm_x0', 'f', 0, 'horizontal center position for mutual intensity cut calculation'],
    ['wm_y0', 'f', 0, 'vertical center position for mutual intensity cut calculation'],
    ['wm_ei', 'i', 0, 'integration over photon energy is required (1) or not (0); if the integration is required, the limits are taken from w_e, w_ef'],
    ['wm_rm', 'i', 1, 'method for generation of pseudo-random numbers for e-beam phase-space integration: 1- standard pseudo-random number generator, 2- Halton sequences, 3- LPtau sequences (to be implemented)'],
    ['wm_am', 'i', 0, 'multi-electron integration approximation method: 0- no approximation (use the standard 5D integration method), 1- integrate numerically only over e-beam energy spread and use convolution to treat transverse emittance'],
    ['wm_fni', 's', 'res_int_pr_me.dat', 'file name for saving propagated multi-e intensity distribution vs horizontal and vertical position'],

    #to add options
    ['op_r', 'f', 20.0, 'longitudinal position of the first optical element [m]'],

    # Former appParam:
    ['rs_type', 's', 't', 'source type, (u) idealized undulator, (t), tabulated undulator, (m) multipole, (g) gaussian beam'],

#---Beamline optics:
    # S0: aperture
    ['op_S0_shape', 's', 'r', 'shape'],
    ['op_S0_Dx', 'f', 0.002, 'horizontalSize'],
    ['op_S0_Dy', 'f', 0.001, 'verticalSize'],
    ['op_S0_x', 'f', 0.0, 'horizontalOffset'],
    ['op_S0_y', 'f', 0.0, 'verticalOffset'],

    # S0_HFM: drift
    ['op_S0_HFM_L', 'f', 1.081, 'length'],

    # HFM: sphericalMirror
    ['op_HFM_hfn', 's', 'None', 'heightProfileFile'],
    ['op_HFM_dim', 's', 'x', 'orientation'],
    ['op_HFM_r', 'f', 8871.45, 'radius'],
    ['op_HFM_size_tang', 'f', 0.95, 'tangentialSize'],
    ['op_HFM_size_sag', 'f', 0.005, 'sagittalSize'],
    ['op_HFM_ang', 'f', 0.0025, 'grazingAngle'],
    ['op_HFM_nvx', 'f', 0.999996875002, 'normalVectorX'],
    ['op_HFM_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_HFM_nvz', 'f', -0.00249999739583, 'normalVectorZ'],
    ['op_HFM_tvx', 'f', 0.00249999739583, 'tangentialVectorX'],
    ['op_HFM_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_HFM_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_HFM_x', 'f', 0.0, 'horizontalOffset'],
    ['op_HFM_y', 'f', 0.0, 'verticalOffset'],

    # HFM_S1: drift
    ['op_HFM_S1_L', 'f', 1.407, 'length'],

    # S1: aperture
    ['op_S1_shape', 's', 'r', 'shape'],
    ['op_S1_Dx', 'f', 0.0024, 'horizontalSize'],
    ['op_S1_Dy', 'f', 0.0015, 'verticalSize'],
    ['op_S1_x', 'f', 0.0, 'horizontalOffset'],
    ['op_S1_y', 'f', 0.0, 'verticalOffset'],

    # S1_DCM_C1: drift
    ['op_S1_DCM_C1_L', 'f', 0.781, 'length'],

    # DCM_C1: crystal
    ['op_DCM_C1_hfn', 's', '', 'heightProfileFile'],
    ['op_DCM_C1_dim', 's', 'x', 'orientation'],
    ['op_DCM_C1_d_sp', 'f', 3.13557135638, 'dSpacing'],
    ['op_DCM_C1_psi0r', 'f', -1.53227839905e-05, 'psi0r'],
    ['op_DCM_C1_psi0i', 'f', 3.59410775406e-07, 'psi0i'],
    ['op_DCM_C1_psiHr', 'f', -8.10706354484e-06, 'psiHr'],
    ['op_DCM_C1_psiHi', 'f', 2.50931132347e-07, 'psiHi'],
    ['op_DCM_C1_psiHBr', 'f', -8.10706354484e-06, 'psiHBr'],
    ['op_DCM_C1_psiHBi', 'f', 2.50931132347e-07, 'psiHBi'],
    ['op_DCM_C1_tc', 'f', 0.01, 'crystalThickness'],
    ['op_DCM_C1_ang_as', 'f', 0.0, 'asymmetryAngle'],
    ['op_DCM_C1_nvx', 'f', -0.968973817886, 'nvx'],
    ['op_DCM_C1_nvy', 'f', 2.59635532439e-08, 'nvy'],
    ['op_DCM_C1_nvz', 'f', -0.247163387763, 'nvz'],
    ['op_DCM_C1_tvx', 'f', -0.247163387763, 'tvx'],
    ['op_DCM_C1_tvy', 'f', 6.62271741473e-09, 'tvy'],
    ['op_DCM_C1_ang', 'f', 0.249751717635, 'grazingAngle'],
    ['op_DCM_C1_amp_coef', 'f', 1.0, 'heightAmplification'],

    # DCM_C2: crystal
    ['op_DCM_C2_hfn', 's', '', 'heightProfileFile'],
    ['op_DCM_C2_dim', 's', 'x', 'orientation'],
    ['op_DCM_C2_d_sp', 'f', 3.13557135638, 'dSpacing'],
    ['op_DCM_C2_psi0r', 'f', -1.53227839905e-05, 'psi0r'],
    ['op_DCM_C2_psi0i', 'f', 3.59410775406e-07, 'psi0i'],
    ['op_DCM_C2_psiHr', 'f', -8.10706354484e-06, 'psiHr'],
    ['op_DCM_C2_psiHi', 'f', 2.50931132347e-07, 'psiHi'],
    ['op_DCM_C2_psiHBr', 'f', -8.10706354484e-06, 'psiHBr'],
    ['op_DCM_C2_psiHBi', 'f', 2.50931132347e-07, 'psiHBi'],
    ['op_DCM_C2_tc', 'f', 0.01, 'crystalThickness'],
    ['op_DCM_C2_ang_as', 'f', 0.0, 'asymmetryAngle'],
    ['op_DCM_C2_nvx', 'f', 0.968973817886, 'nvx'],
    ['op_DCM_C2_nvy', 'f', 0.0, 'nvy'],
    ['op_DCM_C2_nvz', 'f', -0.247163387763, 'nvz'],
    ['op_DCM_C2_tvx', 'f', 0.247163387763, 'tvx'],
    ['op_DCM_C2_tvy', 'f', 0.0, 'tvy'],
    ['op_DCM_C2_ang', 'f', 0.249751717635, 'grazingAngle'],
    ['op_DCM_C2_amp_coef', 'f', 1.0, 'heightAmplification'],

    # DCM_C2_At_BPM1: drift
    ['op_DCM_C2_At_BPM1_L', 'f', 2.2416, 'length'],

    # At_BPM1_Before_SSA: drift
    ['op_At_BPM1_Before_SSA_L', 'f', 11.9668, 'length'],

    # SSA: aperture
    ['op_SSA_shape', 's', 'r', 'shape'],
    ['op_SSA_Dx', 'f', 5e-05, 'horizontalSize'],
    ['op_SSA_Dy', 'f', 0.003, 'verticalSize'],
    ['op_SSA_x', 'f', 0.0, 'horizontalOffset'],
    ['op_SSA_y', 'f', 0.0, 'verticalOffset'],

    # SSA_AKB: drift
    ['op_SSA_AKB_L', 'f', 11.8308, 'length'],

    # AKB: aperture
    ['op_AKB_shape', 's', 'r', 'shape'],
    ['op_AKB_Dx', 'f', 0.003, 'horizontalSize'],
    ['op_AKB_Dy', 'f', 0.000875, 'verticalSize'],
    ['op_AKB_x', 'f', 0.0, 'horizontalOffset'],
    ['op_AKB_y', 'f', 0.0, 'verticalOffset'],

    # AKB_KBV: drift
    ['op_AKB_KBV_L', 'f', 0.175, 'length'],

    # KBV: ellipsoidMirror
    ['op_KBV_hfn', 's', '', 'heightProfileFile'],
    ['op_KBV_dim', 's', 'x', 'orientation'],
    ['op_KBV_p', 'f', 63.913, 'firstFocusLength'],
    ['op_KBV_q', 'f', 0.637, 'focalLength'],
    ['op_KBV_ang', 'f', 0.0025, 'grazingAngle'],
    ['op_KBV_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_KBV_size_tang', 'f', 0.35, 'tangentialSize'],
    ['op_KBV_size_sag', 'f', 0.003, 'sagittalSize'],
    ['op_KBV_nvx', 'f', 0.0, 'normalVectorX'],
    ['op_KBV_nvy', 'f', 0.999996875002, 'normalVectorY'],
    ['op_KBV_nvz', 'f', -0.00249999739583, 'normalVectorZ'],
    ['op_KBV_tvx', 'f', 0.0, 'tangentialVectorX'],
    ['op_KBV_tvy', 'f', -0.00249999739583, 'tangentialVectorY'],
    ['op_KBV_x', 'f', 0.0, 'horizontalOffset'],
    ['op_KBV_y', 'f', 0.0, 'verticalOffset'],

    # KBV_KBH: drift
    ['op_KBV_KBH_L', 'f', 0.337, 'length'],

    # KBH: ellipsoidMirror
    ['op_KBH_hfn', 's', '', 'heightProfileFile'],
    ['op_KBH_dim', 's', 'x', 'orientation'],
    ['op_KBH_p', 'f', 12.3428, 'firstFocusLength'],
    ['op_KBH_q', 'f', 0.3, 'focalLength'],
    ['op_KBH_ang', 'f', 0.0025, 'grazingAngle'],
    ['op_KBH_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_KBH_size_tang', 'f', 0.3, 'tangentialSize'],
    ['op_KBH_size_sag', 'f', 0.003, 'sagittalSize'],
    ['op_KBH_nvx', 'f', 0.999996875002, 'normalVectorX'],
    ['op_KBH_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_KBH_nvz', 'f', -0.00249999739583, 'normalVectorZ'],
    ['op_KBH_tvx', 'f', -0.00249999739583, 'tangentialVectorX'],
    ['op_KBH_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_KBH_x', 'f', 0.0, 'horizontalOffset'],
    ['op_KBH_y', 'f', 0.0, 'verticalOffset'],

    # KBH_At_Sample: drift
    ['op_KBH_At_Sample_L', 'f', 0.3, 'length'],

#---Propagation parameters
    ['op_S0_pp', 'f',                 [0, 0, 1.0, 0, 0, 1.1, 7.0, 1.3, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'S0'],
    ['op_S0_HFM_pp', 'f',             [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'S0_HFM'],
    ['op_HFM_pp', 'f',                [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'HFM'],
    ['op_HFM_S1_pp', 'f',             [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'HFM_S1'],
    ['op_S1_pp', 'f',                 [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'S1'],
    ['op_S1_DCM_C1_pp', 'f',          [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'S1_DCM_C1'],
    ['op_DCM_C1_pp', 'f',             [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'DCM_C1'],
    ['op_DCM_C2_pp', 'f',             [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'DCM_C2'],
    ['op_DCM_C2_At_BPM1_pp', 'f',     [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'DCM_C2_At_BPM1'],
    ['op_At_BPM1_Before_SSA_pp', 'f', [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'At_BPM1_Before_SSA'],
    ['op_SSA_pp', 'f',                [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'SSA'],
    ['op_SSA_AKB_pp', 'f',            [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'SSA_AKB'],
    ['op_AKB_pp', 'f',                [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'AKB'],
    ['op_AKB_KBV_pp', 'f',            [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'AKB_KBV'],
    ['op_KBV_pp', 'f',                [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'KBV'],
    ['op_KBV_KBH_pp', 'f',            [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'KBV_KBH'],
    ['op_KBH_pp', 'f',                [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'KBH'],
    ['op_KBH_At_Sample_pp', 'f',      [0, 0, 1.0, 4, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'KBH_At_Sample'],
    ['op_fin_pp', 'f',                [0, 0, 1.0, 0, 1, 0.5, 1.0, 0.2, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'final post-propagation (resize) parameters'],

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
])

def setup_magnetic_measurement_files(filename, v):
    import os
    import re
    import zipfile
    z = zipfile.ZipFile(filename)
    z.extractall()
    for f in z.namelist():
        if re.search(r'\.txt', f):
            v.und_mfs = os.path.basename(f)
            v.und_mdir = os.path.dirname(f) or './'
            return
    raise RuntimeError('missing magnetic measurement index *.txt file')

def main():
    v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv=True)
    setup_magnetic_measurement_files("magn_meas_srx.zip", v)
    op = set_optics(v)
    v.ss = True
    v.ss_pl = 'e'
    v.sm = True
    v.sm_pl = 'e'
    v.pw = True
    v.pw_pl = 'xy'
    v.si = True
    v.si_pl = 'xy'
    v.tr = True
    v.tr_pl = 'xz'
    v.ws = True
    v.ws_pl = 'xy'
    mag = None
    if v.rs_type == 'm':
        mag = srwlib.SRWLMagFldC()
        mag.arXc.append(0)
        mag.arYc.append(0)
        mag.arMagFld.append(srwlib.SRWLMagFldM(v.mp_field, v.mp_order, v.mp_distribution, v.mp_len))
        mag.arZc.append(v.mp_zc)
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)


if __name__ == '__main__':
    main()
