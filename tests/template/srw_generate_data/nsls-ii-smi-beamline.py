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
    names = ['MOAT_1', 'MOAT_1_MOAT_2', 'MOAT_2', 'MOAT_2_HFM', 'HFM', 'HFM_VFM', 'VFM', 'VFM_VDM', 'VDM', 'VDM_SSA', 'SSA', 'SSA_ES1', 'ES1', 'ES1_CRL', 'CRL', 'CRL_ES2', 'ES2']
    for el_name in names:
        if el_name == 'MOAT_1':
            # MOAT_1: crystal 31.94m
            crystal = srwlib.SRWLOptCryst(
                _d_sp=v.op_MOAT_1_d_sp,
                _psi0r=v.op_MOAT_1_psi0r,
                _psi0i=v.op_MOAT_1_psi0i,
                _psi_hr=v.op_MOAT_1_psiHr,
                _psi_hi=v.op_MOAT_1_psiHi,
                _psi_hbr=v.op_MOAT_1_psiHBr,
                _psi_hbi=v.op_MOAT_1_psiHBi,
                _tc=v.op_MOAT_1_tc,
                _ang_as=v.op_MOAT_1_ang_as,
            )
            crystal.set_orient(
                _nvx=v.op_MOAT_1_nvx,
                _nvy=v.op_MOAT_1_nvy,
                _nvz=v.op_MOAT_1_nvz,
                _tvx=v.op_MOAT_1_tvx,
                _tvy=v.op_MOAT_1_tvy,
            )
            el.append(crystal)
            pp.append(v.op_MOAT_1_pp)
            mirror_file = v.op_MOAT_1_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by MOAT_1 beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_MOAT_1_dim,
                _ang=abs(v.op_MOAT_1_ang),
                _amp_coef=v.op_MOAT_1_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'MOAT_1_MOAT_2':
            # MOAT_1_MOAT_2: drift 31.94m
            el.append(srwlib.SRWLOptD(
                _L=v.op_MOAT_1_MOAT_2_L,
            ))
            pp.append(v.op_MOAT_1_MOAT_2_pp)
        elif el_name == 'MOAT_2':
            # MOAT_2: crystal 31.99m
            crystal = srwlib.SRWLOptCryst(
                _d_sp=v.op_MOAT_2_d_sp,
                _psi0r=v.op_MOAT_2_psi0r,
                _psi0i=v.op_MOAT_2_psi0i,
                _psi_hr=v.op_MOAT_2_psiHr,
                _psi_hi=v.op_MOAT_2_psiHi,
                _psi_hbr=v.op_MOAT_2_psiHBr,
                _psi_hbi=v.op_MOAT_2_psiHBi,
                _tc=v.op_MOAT_2_tc,
                _ang_as=v.op_MOAT_2_ang_as,
            )
            crystal.set_orient(
                _nvx=v.op_MOAT_2_nvx,
                _nvy=v.op_MOAT_2_nvy,
                _nvz=v.op_MOAT_2_nvz,
                _tvx=v.op_MOAT_2_tvx,
                _tvy=v.op_MOAT_2_tvy,
            )
            el.append(crystal)
            pp.append(v.op_MOAT_2_pp)
            
        elif el_name == 'MOAT_2_HFM':
            # MOAT_2_HFM: drift 31.99m
            el.append(srwlib.SRWLOptD(
                _L=v.op_MOAT_2_HFM_L,
            ))
            pp.append(v.op_MOAT_2_HFM_pp)
        elif el_name == 'HFM':
            # HFM: sphericalMirror 34.88244m
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
            mirror_file = v.op_HFM_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by HFM beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_HFM_dim,
                _ang=abs(v.op_HFM_ang),
                _amp_coef=v.op_HFM_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'HFM_VFM':
            # HFM_VFM: drift 34.88244m
            el.append(srwlib.SRWLOptD(
                _L=v.op_HFM_VFM_L,
            ))
            pp.append(v.op_HFM_VFM_pp)
        elif el_name == 'VFM':
            # VFM: sphericalMirror 38.30244m
            el.append(srwlib.SRWLOptMirSph(
                _r=v.op_VFM_r,
                _size_tang=v.op_VFM_size_tang,
                _size_sag=v.op_VFM_size_sag,
                _nvx=v.op_VFM_nvx,
                _nvy=v.op_VFM_nvy,
                _nvz=v.op_VFM_nvz,
                _tvx=v.op_VFM_tvx,
                _tvy=v.op_VFM_tvy,
                _x=v.op_VFM_x,
                _y=v.op_VFM_y,
            ))
            pp.append(v.op_VFM_pp)
            mirror_file = v.op_VFM_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by VFM beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_VFM_dim,
                _ang=abs(v.op_VFM_ang),
                _amp_coef=v.op_VFM_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'VFM_VDM':
            # VFM_VDM: drift 38.30244m
            el.append(srwlib.SRWLOptD(
                _L=v.op_VFM_VDM_L,
            ))
            pp.append(v.op_VFM_VDM_pp)
        elif el_name == 'VDM':
            # VDM: sphericalMirror 39.0m
            el.append(srwlib.SRWLOptMirSph(
                _r=v.op_VDM_r,
                _size_tang=v.op_VDM_size_tang,
                _size_sag=v.op_VDM_size_sag,
                _nvx=v.op_VDM_nvx,
                _nvy=v.op_VDM_nvy,
                _nvz=v.op_VDM_nvz,
                _tvx=v.op_VDM_tvx,
                _tvy=v.op_VDM_tvy,
                _x=v.op_VDM_x,
                _y=v.op_VDM_y,
            ))
            pp.append(v.op_VDM_pp)
            mirror_file = v.op_VDM_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by VDM beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_VDM_dim,
                _ang=abs(v.op_VDM_ang),
                _amp_coef=v.op_VDM_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'VDM_SSA':
            # VDM_SSA: drift 39.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_VDM_SSA_L,
            ))
            pp.append(v.op_VDM_SSA_pp)
        elif el_name == 'SSA':
            # SSA: aperture 47.00244m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_SSA_shape,
                _ap_or_ob='a',
                _Dx=v.op_SSA_Dx,
                _Dy=v.op_SSA_Dy,
                _x=v.op_SSA_x,
                _y=v.op_SSA_y,
            ))
            pp.append(v.op_SSA_pp)
        elif el_name == 'SSA_ES1':
            # SSA_ES1: drift 47.00244m
            el.append(srwlib.SRWLOptD(
                _L=v.op_SSA_ES1_L,
            ))
            pp.append(v.op_SSA_ES1_pp)
        elif el_name == 'ES1':
            # ES1: watch 50.9m
            pass
        elif el_name == 'ES1_CRL':
            # ES1_CRL: drift 50.9m
            el.append(srwlib.SRWLOptD(
                _L=v.op_ES1_CRL_L,
            ))
            pp.append(v.op_ES1_CRL_pp)
        elif el_name == 'CRL':
            # CRL: crl 57.335m
            el.append(srwlib.srwl_opt_setup_CRL(
                _foc_plane=v.op_CRL_foc_plane,
                _delta=v.op_CRL_delta,
                _atten_len=v.op_CRL_atten_len,
                _shape=v.op_CRL_shape,
                _apert_h=v.op_CRL_apert_h,
                _apert_v=v.op_CRL_apert_v,
                _r_min=v.op_CRL_r_min,
                _n=v.op_CRL_n,
                _wall_thick=v.op_CRL_wall_thick,
                _xc=v.op_CRL_x,
                _yc=v.op_CRL_y,
            ))
            pp.append(v.op_CRL_pp)
        elif el_name == 'CRL_ES2':
            # CRL_ES2: drift 57.335m
            el.append(srwlib.SRWLOptD(
                _L=v.op_CRL_ES2_L,
            ))
            pp.append(v.op_CRL_ES2_pp)
        elif el_name == 'ES2':
            # ES2: watch 59.0m
            pass
    pp.append(v.op_fin_pp)
    return srwlib.SRWLOptC(el, pp)


varParam = srwl_bl.srwl_uti_ext_options([
    ['name', 's', 'NSLS-II SMI beamline', 'simulation name'],

#---Data Folder
    ['fdir', 's', '', 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', 'NSLS-II High Beta Day 1', 'standard electron beam name'],
    ['ebm_nms', 's', '', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', 0.5, 'electron beam current [A]'],
    ['ebm_e', 'f', 3.0, 'electron beam avarage energy [GeV]'],
    ['ebm_de', 'f', 0.0, 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', 0.0, 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', 0.0, 'electron beam initial average vertical position [m]'],
    ['ebm_xp', 'f', 0.0, 'electron beam initial average horizontal angle [rad]'],
    ['ebm_yp', 'f', 0.0, 'electron beam initial average vertical angle [rad]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', -1.44325, 'electron beam longitudinal drift [m] to be performed before a required calculation'],
    ['ebm_ens', 'f', 0.00089, 'electron beam relative energy spread'],
    ['ebm_emx', 'f', 9e-10, 'electron beam horizontal emittance [m]'],
    ['ebm_emy', 'f', 8e-12, 'electron beam vertical emittance [m]'],
    # Definition of the beam through Twiss:
    ['ebm_betax', 'f', 20.85, 'horizontal beta-function [m]'],
    ['ebm_betay', 'f', 3.4, 'vertical beta-function [m]'],
    ['ebm_alphax', 'f', 0.0, 'horizontal alpha-function [rad]'],
    ['ebm_alphay', 'f', 0.0, 'vertical alpha-function [rad]'],
    ['ebm_etax', 'f', 0.0, 'horizontal dispersion function [m]'],
    ['ebm_etay', 'f', 0.0, 'vertical dispersion function [m]'],
    ['ebm_etaxp', 'f', 0.0, 'horizontal dispersion function derivative [rad]'],
    ['ebm_etayp', 'f', 0.0, 'vertical dispersion function derivative [rad]'],
    # Definition of the beam through Moments:
    ['ebm_sigx', 'f', 0.000136985400682, 'horizontal RMS size of electron beam [m]'],
    ['ebm_sigy', 'f', 5.21536192416e-06, 'vertical RMS size of electron beam [m]'],
    ['ebm_sigxp', 'f', 6.57004319818e-06, 'horizontal RMS angular divergence of electron beam [rad]'],
    ['ebm_sigyp', 'f', 1.53392997769e-06, 'vertical RMS angular divergence of electron beam [rad]'],
    ['ebm_mxxp', 'f', 0.0, 'horizontal position-angle mixed 2nd order moment of electron beam [m]'],
    ['ebm_myyp', 'f', 0.0, 'vertical position-angle mixed 2nd order moment of electron beam [m]'],

#---Undulator
    ['und_bx', 'f', 0.0, 'undulator horizontal peak magnetic field [T]'],
    ['und_by', 'f', 0.955, 'undulator vertical peak magnetic field [T]'],
    ['und_phx', 'f', 0.0, 'initial phase of the horizontal magnetic field [rad]'],
    ['und_phy', 'f', 0.0, 'initial phase of the vertical magnetic field [rad]'],
    ['und_b2e', '', '', 'estimate undulator fundamental photon energy (in [eV]) for the amplitude of sinusoidal magnetic field defined by und_b or und_bx, und_by', 'store_true'],
    ['und_e2b', '', '', 'estimate undulator field amplitude (in [T]) for the photon energy defined by w_e', 'store_true'],
    ['und_per', 'f', 0.023, 'undulator period [m]'],
    ['und_len', 'f', 2.7945, 'undulator length [m]'],
    ['und_zc', 'f', 0.6, 'undulator center longitudinal position [m]'],
    ['und_sx', 'i', 1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    ['und_sy', 'i', -1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    ['und_g', 'f', 6.72, 'undulator gap [mm] (assumes availability of magnetic measurement or simulation data)'],
    ['und_ph', 'f', 0.0, 'shift of magnet arrays [mm] for which the field should be set up'],
    ['und_mdir', 's', '', 'name of magnetic measurements sub-folder'],
    ['und_mfs', 's', '', 'name of magnetic measurements for different gaps summary file'],



#---Calculation Types
    # Electron Trajectory
    ['tr', '', '', 'calculate electron trajectory', 'store_true'],
    ['tr_cti', 'f', 0.0, 'initial time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_ctf', 'f', 0.0, 'final time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_np', 'f', 10000, 'number of points for trajectory calculation'],
    ['tr_mag', 'i', 1, 'magnetic field to be used for trajectory calculation: 1- approximate, 2- accurate'],
    ['tr_fn', 's', 'res_trj.dat', 'file name for saving calculated trajectory data'],
    ['tr_pl', 's', '', 'plot the resulting trajectiry in graph(s): ""- dont plot, otherwise the string should list the trajectory components to plot'],

    #Single-Electron Spectrum vs Photon Energy
    ['ss', '', '', 'calculate single-e spectrum vs photon energy', 'store_true'],
    ['ss_ei', 'f', 20000.0, 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 20400.0, 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 10000, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_x', 'f', 0.0, 'horizontal position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_y', 'f', 0.0, 'vertical position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_meth', 'i', 1, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['ss_prec', 'f', 0.01, 'relative precision for single-e spectrum vs photon energy calculation (nominal value is 0.01)'],
    ['ss_pol', 'i', 6, 'polarization component to extract after spectrum vs photon energy calculation: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['ss_mag', 'i', 1, 'magnetic field to be used for single-e spectrum vs photon energy calculation: 1- approximate, 2- accurate'],
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
    ['pw_rx', 'f', 0.015, 'range of horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_nx', 'i', 100, 'number of points vs horizontal position for calculation of power density distribution'],
    ['pw_y', 'f', 0.0, 'central vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ry', 'f', 0.015, 'range of vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ny', 'i', 100, 'number of points vs vertical position for calculation of power density distribution'],
    ['pw_pr', 'f', 1.0, 'precision factor for calculation of power density distribution'],
    ['pw_meth', 'i', 1, 'power density computation method (1- "near field", 2- "far field")'],
    ['pw_zst', 'f', 0., 'initial longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_zfi', 'f', 0., 'final longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_mag', 'i', 1, 'magnetic field to be used for power density calculation: 1- approximate, 2- accurate'],
    ['pw_fn', 's', 'res_pow.dat', 'file name for saving calculated power density distribution'],
    ['pw_pl', 's', '', 'plot the resulting power density distribution in a graph: ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    #Single-Electron Intensity distribution vs horizontal and vertical position
    ['si', '', '', 'calculate single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position', 'store_true'],
    #Single-Electron Wavefront Propagation
    ['ws', '', '', 'calculate single-electron (/ fully coherent) wavefront propagation', 'store_true'],
    #Multi-Electron (partially-coherent) Wavefront Propagation
    ['wm', '', '', 'calculate multi-electron (/ partially coherent) wavefront propagation', 'store_true'],

    ['w_e', 'f', 20358.0, 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1.0, 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', 0.0, 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', 0.0004, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 100, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', 0.0, 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', 0.0004, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 100, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', 1.5, 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', 1, 'method to use for calculation of intensity distribution vs horizontal and vertical position: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['w_prec', 'f', 0.01, 'relative precision for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_u', 'i', 1, 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    ['si_pol', 'i', 6, 'polarization component to extract after calculation of intensity distribution: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['si_type', 'i', 0, 'type of a characteristic to be extracted after calculation of intensity distribution: 0- Single-Electron Intensity, 1- Multi-Electron Intensity, 2- Single-Electron Flux, 3- Multi-Electron Flux, 4- Single-Electron Radiation Phase, 5- Re(E): Real part of Single-Electron Electric Field, 6- Im(E): Imaginary part of Single-Electron Electric Field, 7- Single-Electron Intensity, integrated over Time or Photon Energy'],
    ['w_mag', 'i', 1, 'magnetic field to be used for calculation of intensity distribution vs horizontal and vertical position: 1- approximate, 2- accurate'],

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
    ['rs_type', 's', 'u', 'source type, (u) idealized undulator, (t), tabulated undulator, (m) multipole, (g) gaussian beam'],

#---Beamline optics:
    # MOAT_1: crystal
    ['op_MOAT_1_hfn', 's', 'Si_heat204.dat', 'heightProfileFile'],
    ['op_MOAT_1_dim', 's', 'y', 'orientation'],
    ['op_MOAT_1_d_sp', 'f', 3.13557135638, 'dSpacing'],
    ['op_MOAT_1_psi0r', 'f', -2.33400050166e-06, 'psi0r'],
    ['op_MOAT_1_psi0i', 'f', 8.59790386417e-09, 'psi0i'],
    ['op_MOAT_1_psiHr', 'f', -1.22944507993e-06, 'psiHr'],
    ['op_MOAT_1_psiHi', 'f', 6.00282990962e-09, 'psiHi'],
    ['op_MOAT_1_psiHBr', 'f', -1.22944507993e-06, 'psiHBr'],
    ['op_MOAT_1_psiHBi', 'f', 6.00282990962e-09, 'psiHBi'],
    ['op_MOAT_1_tc', 'f', 0.01, 'crystalThickness'],
    ['op_MOAT_1_ang_as', 'f', 0.0, 'asymmetryAngle'],
    ['op_MOAT_1_nvx', 'f', -0.0966554453406, 'nvx'],
    ['op_MOAT_1_nvy', 'f', 0.990567587399, 'nvy'],
    ['op_MOAT_1_nvz', 'f', -0.0971266167475, 'nvz'],
    ['op_MOAT_1_tvx', 'f', -0.00943241252825, 'tvx'],
    ['op_MOAT_1_tvy', 'f', 0.0966675192333, 'tvy'],
    ['op_MOAT_1_ang', 'f', 0.0972799772892, 'grazingAngle'],
    ['op_MOAT_1_amp_coef', 'f', 1.0, 'heightAmplification'],

    # MOAT_1_MOAT_2: drift
    ['op_MOAT_1_MOAT_2_L', 'f', 0.05, 'length'],

    # MOAT_2: crystal
    ['op_MOAT_2_hfn', 's', 'None', 'heightProfileFile'],
    ['op_MOAT_2_dim', 's', 'x', 'orientation'],
    ['op_MOAT_2_d_sp', 'f', 3.13557135638, 'dSpacing'],
    ['op_MOAT_2_psi0r', 'f', -2.33400050166e-06, 'psi0r'],
    ['op_MOAT_2_psi0i', 'f', 8.59790386417e-09, 'psi0i'],
    ['op_MOAT_2_psiHr', 'f', -1.22944507993e-06, 'psiHr'],
    ['op_MOAT_2_psiHi', 'f', 6.00282990962e-09, 'psiHi'],
    ['op_MOAT_2_psiHBr', 'f', -1.22944507993e-06, 'psiHBr'],
    ['op_MOAT_2_psiHBi', 'f', 6.00282990962e-09, 'psiHBi'],
    ['op_MOAT_2_tc', 'f', 0.01, 'crystalThickness'],
    ['op_MOAT_2_ang_as', 'f', 0.0, 'asymmetryAngle'],
    ['op_MOAT_2_nvx', 'f', 0.0966554453406, 'nvx'],
    ['op_MOAT_2_nvy', 'f', 0.990567587399, 'nvy'],
    ['op_MOAT_2_nvz', 'f', -0.0971266167475, 'nvz'],
    ['op_MOAT_2_tvx', 'f', 0.00943241252825, 'tvx'],
    ['op_MOAT_2_tvy', 'f', 0.0966675192333, 'tvy'],
    ['op_MOAT_2_ang', 'f', 0.0972799772892, 'grazingAngle'],
    ['op_MOAT_2_amp_coef', 'f', 1.0, 'heightAmplification'],

    # MOAT_2_HFM: drift
    ['op_MOAT_2_HFM_L', 'f', 2.89244, 'length'],

    # HFM: sphericalMirror
    ['op_HFM_hfn', 's', 'HFM_Rh7.6km.dat', 'heightProfileFile'],
    ['op_HFM_dim', 's', 'x', 'orientation'],
    ['op_HFM_r', 'f', 7100.0, 'radius'],
    ['op_HFM_size_tang', 'f', 0.5, 'tangentialSize'],
    ['op_HFM_size_sag', 'f', 0.04, 'sagittalSize'],
    ['op_HFM_ang', 'f', 0.003141592654, 'grazingAngle'],
    ['op_HFM_nvx', 'f', 0.999995065202, 'normalVectorX'],
    ['op_HFM_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_HFM_nvz', 'f', -0.00314158748629, 'normalVectorZ'],
    ['op_HFM_tvx', 'f', 0.00314158748629, 'tangentialVectorX'],
    ['op_HFM_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_HFM_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_HFM_x', 'f', 0.0, 'horizontalOffset'],
    ['op_HFM_y', 'f', 0.0, 'verticalOffset'],

    # HFM_VFM: drift
    ['op_HFM_VFM_L', 'f', 3.42, 'length'],

    # VFM: sphericalMirror
    ['op_VFM_hfn', 's', 'VFM_Rh5.4km.dat', 'heightProfileFile'],
    ['op_VFM_dim', 's', 'y', 'orientation'],
    ['op_VFM_r', 'f', 6100.0, 'radius'],
    ['op_VFM_size_tang', 'f', 0.4, 'tangentialSize'],
    ['op_VFM_size_sag', 'f', 0.04, 'sagittalSize'],
    ['op_VFM_ang', 'f', 0.003141592654, 'grazingAngle'],
    ['op_VFM_nvx', 'f', 0.0, 'normalVectorX'],
    ['op_VFM_nvy', 'f', 0.999995065202, 'normalVectorY'],
    ['op_VFM_nvz', 'f', -0.00314158748629, 'normalVectorZ'],
    ['op_VFM_tvx', 'f', 0.0, 'tangentialVectorX'],
    ['op_VFM_tvy', 'f', 0.00314158748629, 'tangentialVectorY'],
    ['op_VFM_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_VFM_x', 'f', 0.0, 'horizontalOffset'],
    ['op_VFM_y', 'f', 0.0, 'verticalOffset'],

    # VFM_VDM: drift
    ['op_VFM_VDM_L', 'f', 0.69756, 'length'],

    # VDM: sphericalMirror
    ['op_VDM_hfn', 's', 'VDM.dat', 'heightProfileFile'],
    ['op_VDM_dim', 's', 'y', 'orientation'],
    ['op_VDM_r', 'f', 300000.0, 'radius'],
    ['op_VDM_size_tang', 'f', 0.4, 'tangentialSize'],
    ['op_VDM_size_sag', 'f', 0.04, 'sagittalSize'],
    ['op_VDM_ang', 'f', 0.0031415926, 'grazingAngle'],
    ['op_VDM_nvx', 'f', 0.0, 'normalVectorX'],
    ['op_VDM_nvy', 'f', 0.999995065202, 'normalVectorY'],
    ['op_VDM_nvz', 'f', -0.00314158743229, 'normalVectorZ'],
    ['op_VDM_tvx', 'f', 0.0, 'tangentialVectorX'],
    ['op_VDM_tvy', 'f', 0.00314158743229, 'tangentialVectorY'],
    ['op_VDM_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_VDM_x', 'f', 0.0, 'horizontalOffset'],
    ['op_VDM_y', 'f', 0.0, 'verticalOffset'],

    # VDM_SSA: drift
    ['op_VDM_SSA_L', 'f', 8.00244, 'length'],

    # SSA: aperture
    ['op_SSA_shape', 's', 'r', 'shape'],
    ['op_SSA_Dx', 'f', 0.0004, 'horizontalSize'],
    ['op_SSA_Dy', 'f', 0.0004, 'verticalSize'],
    ['op_SSA_x', 'f', 0.0, 'horizontalOffset'],
    ['op_SSA_y', 'f', 0.0, 'verticalOffset'],

    # SSA_ES1: drift
    ['op_SSA_ES1_L', 'f', 3.89756, 'length'],

    # ES1_CRL: drift
    ['op_ES1_CRL_L', 'f', 6.435, 'length'],

    # CRL: crl
    ['op_CRL_foc_plane', 'f', 3, 'focalPlane'],
    ['op_CRL_delta', 'f', 8.211821e-07, 'refractiveIndex'],
    ['op_CRL_atten_len', 'f', 0.028541, 'attenuationLength'],
    ['op_CRL_shape', 'f', 1, 'shape'],
    ['op_CRL_apert_h', 'f', 0.001, 'horizontalApertureSize'],
    ['op_CRL_apert_v', 'f', 0.001, 'verticalApertureSize'],
    ['op_CRL_r_min', 'f', 5e-05, 'tipRadius'],
    ['op_CRL_wall_thick', 'f', 3.24e-05, 'tipWallThickness'],
    ['op_CRL_x', 'f', 0.0, 'horizontalOffset'],
    ['op_CRL_y', 'f', 0.0, 'verticalOffset'],
    ['op_CRL_n', 'i', 23, 'numberOfLenses'],

    # CRL_ES2: drift
    ['op_CRL_ES2_L', 'f', 1.665, 'length'],

#---Propagation parameters
    ['op_MOAT_1_pp', 'f',        [0, 0, 1.0, 0, 0, 3.0, 1.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'MOAT_1'],
    ['op_MOAT_1_MOAT_2_pp', 'f', [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'MOAT_1_MOAT_2'],
    ['op_MOAT_2_pp', 'f',        [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'MOAT_2'],
    ['op_MOAT_2_HFM_pp', 'f',    [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'MOAT_2_HFM'],
    ['op_HFM_pp', 'f',           [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'HFM'],
    ['op_HFM_VFM_pp', 'f',       [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'HFM_VFM'],
    ['op_VFM_pp', 'f',           [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'VFM'],
    ['op_VFM_VDM_pp', 'f',       [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'VFM_VDM'],
    ['op_VDM_pp', 'f',           [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'VDM'],
    ['op_VDM_SSA_pp', 'f',       [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'VDM_SSA'],
    ['op_SSA_pp', 'f',           [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'SSA'],
    ['op_SSA_ES1_pp', 'f',       [0, 0, 1.0, 1, 0, 0.5, 5.0, 0.5, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'SSA_ES1'],
    ['op_ES1_CRL_pp', 'f',       [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'ES1_CRL'],
    ['op_CRL_pp', 'f',           [0, 0, 1.0, 2, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'CRL'],
    ['op_CRL_ES2_pp', 'f',       [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'CRL_ES2'],
    ['op_fin_pp', 'f',           [0, 0, 1.0, 0, 0, 0.4, 3.0, 0.4, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'final post-propagation (resize) parameters'],

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


def main():
    v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv=True)
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
