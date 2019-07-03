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
    names = ['VFM', 'VFM_HFM', 'HFM', 'HFM_Watchpoint', 'Watchpoint', 'Watchpoint_Mask', 'Mask', 'Watchpoint2']
    for el_name in names:
        if el_name == 'VFM':
            # VFM: ellipsoidMirror 50.0m
            el.append(srwlib.SRWLOptMirEl(
                _p=v.op_VFM_p,
                _q=v.op_VFM_q,
                _ang_graz=v.op_VFM_ang,
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
            
        elif el_name == 'VFM_HFM':
            # VFM_HFM: drift 50.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_VFM_HFM_L,
            ))
            pp.append(v.op_VFM_HFM_pp)
        elif el_name == 'HFM':
            # HFM: ellipsoidMirror 50.2m
            el.append(srwlib.SRWLOptMirEl(
                _p=v.op_HFM_p,
                _q=v.op_HFM_q,
                _ang_graz=v.op_HFM_ang,
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
            
        elif el_name == 'HFM_Watchpoint':
            # HFM_Watchpoint: drift 50.2m
            el.append(srwlib.SRWLOptD(
                _L=v.op_HFM_Watchpoint_L,
            ))
            pp.append(v.op_HFM_Watchpoint_pp)
        elif el_name == 'Watchpoint':
            # Watchpoint: watch 50.4m
            pass
        elif el_name == 'Watchpoint_Mask':
            # Watchpoint_Mask: drift 50.4m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Watchpoint_Mask_L,
            ))
            pp.append(v.op_Watchpoint_Mask_pp)
        elif el_name == 'Mask':
            # Mask: mask 50.6m
            el.append(srwlib.srwl_opt_setup_mask(
                _delta=v.op_Mask_delta,
                _atten_len=v.op_Mask_atten_len,
                _thick=v.op_Mask_thick,
                _grid_sh=v.op_Mask_grid_sh,
                _grid_dx=v.op_Mask_grid_dx,
                _grid_dy=v.op_Mask_grid_dy,
                _pitch_x=v.op_Mask_pitch_x,
                _pitch_y=v.op_Mask_pitch_y,
                _grid_nx=v.op_Mask_grid_nx,
                _grid_ny=v.op_Mask_grid_ny,
                _mask_Nx=v.op_Mask_mask_Nx,
                _mask_Ny=v.op_Mask_mask_Ny,
                _grid_angle=v.op_Mask_gridTiltAngle,
                _hx=v.op_Mask_hx,
                _hy=v.op_Mask_hy,
                _mask_x0=v.op_Mask_mask_x0,
                _mask_y0=v.op_Mask_mask_y0,
            ))
            pp.append(v.op_Mask_pp)
        elif el_name == 'Watchpoint2':
            # Watchpoint2: watch 50.6m
            pass
    pp.append(v.op_fin_pp)
    return srwlib.SRWLOptC(el, pp)


varParam = srwl_bl.srwl_uti_ext_options([
    ['name', 's', 'Mask example', 'simulation name'],

#---Data Folder
    ['fdir', 's', '', 'folder (directory) name for reading-in input and saving output data files'],


    ['gbm_x', 'f', 0.0, 'average horizontal coordinates of waist [m]'],
    ['gbm_y', 'f', 0.0, 'average vertical coordinates of waist [m]'],
    ['gbm_z', 'f', 0.0, 'average longitudinal coordinate of waist [m]'],
    ['gbm_xp', 'f', 0.0, 'average horizontal angle at waist [rad]'],
    ['gbm_yp', 'f', 0.0, 'average verical angle at waist [rad]'],
    ['gbm_ave', 'f', 9000.0, 'average photon energy [eV]'],
    ['gbm_pen', 'f', 0.001, 'energy per pulse [J]'],
    ['gbm_rep', 'f', 1, 'rep. rate [Hz]'],
    ['gbm_pol', 'f', 1, 'polarization 1- lin. hor., 2- lin. vert., 3- lin. 45 deg., 4- lin.135 deg., 5- circ. right, 6- circ. left'],
    ['gbm_sx', 'f', 3e-06, 'rms beam size vs horizontal position [m] at waist (for intensity)'],
    ['gbm_sy', 'f', 3e-06, 'rms beam size vs vertical position [m] at waist (for intensity)'],
    ['gbm_st', 'f', 1e-13, 'rms pulse duration [s] (for intensity)'],
    ['gbm_mx', 'f', 0, 'transverse Gauss-Hermite mode order in horizontal direction'],
    ['gbm_my', 'f', 0, 'transverse Gauss-Hermite mode order in vertical direction'],
    ['gbm_ca', 's', 'c', 'treat _sigX, _sigY as sizes in [m] in coordinate representation (_presCA="c") or as angular divergences in [rad] in angular representation (_presCA="a")'],
    ['gbm_ft', 's', 't', 'treat _sigT as pulse duration in [s] in time domain/representation (_presFT="t") or as bandwidth in [eV] in frequency domain/representation (_presFT="f")'],

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
    ['ss_ei', 'f', 100.0, 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 20000.0, 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
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

    ['w_e', 'f', 9000.0, 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1.0, 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', 0.0, 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', 0.002, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 2048, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', 0.0, 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', 0.002, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 2048, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', 0, 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', 2, 'method to use for calculation of intensity distribution vs horizontal and vertical position: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
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
    ['rs_type', 's', 'g', 'source type, (u) idealized undulator, (t), tabulated undulator, (m) multipole, (g) gaussian beam'],

#---Beamline optics:
    # VFM: ellipsoidMirror
    ['op_VFM_hfn', 's', 'None', 'heightProfileFile'],
    ['op_VFM_dim', 's', 'x', 'orientation'],
    ['op_VFM_p', 'f', 50.0, 'firstFocusLength'],
    ['op_VFM_q', 'f', 0.4, 'focalLength'],
    ['op_VFM_ang', 'f', 0.003, 'grazingAngle'],
    ['op_VFM_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_VFM_size_tang', 'f', 0.2, 'tangentialSize'],
    ['op_VFM_size_sag', 'f', 0.01, 'sagittalSize'],
    ['op_VFM_nvx', 'f', 0.0, 'normalVectorX'],
    ['op_VFM_nvy', 'f', 0.999995500003, 'normalVectorY'],
    ['op_VFM_nvz', 'f', -0.0029999955, 'normalVectorZ'],
    ['op_VFM_tvx', 'f', 0.0, 'tangentialVectorX'],
    ['op_VFM_tvy', 'f', -0.0029999955, 'tangentialVectorY'],
    ['op_VFM_x', 'f', 0.0, 'horizontalOffset'],
    ['op_VFM_y', 'f', 0.0, 'verticalOffset'],

    # VFM_HFM: drift
    ['op_VFM_HFM_L', 'f', 0.2, 'length'],

    # HFM: ellipsoidMirror
    ['op_HFM_hfn', 's', 'None', 'heightProfileFile'],
    ['op_HFM_dim', 's', 'x', 'orientation'],
    ['op_HFM_p', 'f', 50.0, 'firstFocusLength'],
    ['op_HFM_q', 'f', 0.2, 'focalLength'],
    ['op_HFM_ang', 'f', 0.003, 'grazingAngle'],
    ['op_HFM_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_HFM_size_tang', 'f', 0.2, 'tangentialSize'],
    ['op_HFM_size_sag', 'f', 0.01, 'sagittalSize'],
    ['op_HFM_nvx', 'f', 0.999995500003, 'normalVectorX'],
    ['op_HFM_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_HFM_nvz', 'f', -0.0029999955, 'normalVectorZ'],
    ['op_HFM_tvx', 'f', -0.0029999955, 'tangentialVectorX'],
    ['op_HFM_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_HFM_x', 'f', 0.0, 'horizontalOffset'],
    ['op_HFM_y', 'f', 0.0, 'verticalOffset'],

    # HFM_Watchpoint: drift
    ['op_HFM_Watchpoint_L', 'f', 0.2, 'length'],

    # Watchpoint_Mask: drift
    ['op_Watchpoint_Mask_L', 'f', 0.2, 'length'],

    # Mask: mask
    ['op_Mask_delta', 'f', 1.0, 'refractiveIndex'],
    ['op_Mask_atten_len', 'f', 1.0, 'attenuationLength'],
    ['op_Mask_thick', 'f', 1.0, 'maskThickness'],
    ['op_Mask_grid_sh', 'f', 0, 'gridShape'],
    ['op_Mask_grid_dx', 'f', 5e-06, 'horizontalGridDimension'],
    ['op_Mask_grid_dy', 'f', 5e-06, 'verticalGridDimension'],
    ['op_Mask_pitch_x', 'f', 2e-05, 'horizontalGridPitch'],
    ['op_Mask_pitch_y', 'f', 2e-05, 'verticalGridPitch'],
    ['op_Mask_gridTiltAngle', 'f', 0.436332312999, 'gridTiltAngle'],
    ['op_Mask_hx', 'f', 7.32e-07, 'horizontalSamplingInterval'],
    ['op_Mask_hy', 'f', 7.32e-07, 'verticalSamplingInterval'],
    ['op_Mask_mask_x0', 'f', 0.0, 'horizontalMaskCoordinate'],
    ['op_Mask_mask_y0', 'f', 0.0, 'verticalMaskCoordinate'],
    ['op_Mask_mask_Nx', 'i', 1024, 'horizontalPixelsNumber'],
    ['op_Mask_mask_Ny', 'i', 1024, 'verticalPixelsNumber'],
    ['op_Mask_grid_nx', 'i', 21, 'horizontalGridsNumber'],
    ['op_Mask_grid_ny', 'i', 21, 'verticalGridsNumber'],

#---Propagation parameters
    ['op_VFM_pp', 'f',             [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'VFM'],
    ['op_VFM_HFM_pp', 'f',         [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'VFM_HFM'],
    ['op_HFM_pp', 'f',             [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'HFM'],
    ['op_HFM_Watchpoint_pp', 'f',  [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'HFM_Watchpoint'],
    ['op_Watchpoint_Mask_pp', 'f', [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Watchpoint_Mask'],
    ['op_Mask_pp', 'f',            [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Mask'],
    ['op_fin_pp', 'f',             [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'final post-propagation (resize) parameters'],

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
    v.si = True
    v.si_pl = 'xy'
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
