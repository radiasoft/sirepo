import re

TEMPLATE = '''

from srwl_bl import SRWLOptA, SRWLOptC, SRWLOptD, SRWLOptL
from srwlib import srwl_uti_read_data_cols, srwl_opt_setup_surf_height_1d, srwl_opt_setup_CRL

varParam = [

    ['name', 's', '{simulation_name}', 'simulation name'],

#---Data Folder
    ['fdir', 's', '', 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', '{electronBeam_beamName_name}', 'standard electron beam name'],
    ['ebm_nms', 's', '', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', {electronBeam_current}, 'electron beam current [A]'],
    ['ebm_de', 'f', {electronBeam_energyDeviation}, 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', {electronBeam_horizontalPosition}, 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', {electronBeam_verticalPosition}, 'electron beam initial average vertical position [m]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', {electronBeamInitialDrift}, 'electron beam longitudinal drift [m] to be performed before a required calculation'],

#---Undulator
    ['und_b', 's', '1', 'use undulator'],
    ['und_bx', 'f', {undulator_horizontalAmplitude}, 'undulator horizontal peak magnetic field [T]'],
    ['und_by', 'f', {undulator_verticalAmplitude}, 'undulator vertical peak magnetic field [T]'],
    ['und_phx', 'f', {undulator_horizontalInitialPhase}, 'initial phase of the horizontal magnetic field [rad]'],
    ['und_phy', 'f', {undulator_verticalInitialPhase}, 'initial phase of the vertical magnetic field [rad]'],
    ['und_b2e', '', '', 'estimate undulator fundamental photon energy (in [eV]) for the amplitude of sinusoidal magnetic field defined by und_b or und_bx, und_by', 'store_true'],
    ['und_e2b', '', '', 'estimate undulator field amplitude (in [T]) for the photon energy defined by w_e', 'store_true'],
    ['und_per', 'f', {undulator_period}, 'undulator period [m]'],
    ['und_len', 'f', {undulator_length}, 'undulator length [m]'],
    ['und_zc', 'f', {undulator_longitudinalPosition}, 'undulator center longitudinal position [m]'],
    ['und_sx', 'i', {undulator_horizontalSymmetry}, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    ['und_sy', 'i', {undulator_verticalSymmetry}, 'undulator vertical magnetic field symmetry vs longitudinal position'],

#---Calculation Types
    #Single-Electron Spectrum vs Photon Energy
    ['ss', '', '', 'calculate single-e spectrum vs photon energy', 'store_true'],
    ['ss_ei', 'f', {intensityReport_initialEnergy}, 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', {intensityReport_finalEnergy}, 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 10000, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_x', 'f', {intensityReport_horizontalPosition}, 'horizontal position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_y', 'f', {intensityReport_verticalPosition}, 'vertical position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_meth', 'i', {intensityReport_method}, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['ss_prec', 'f', {intensityReport_precision}, 'relative precision for single-e spectrum vs photon energy calculation (nominal value is 0.01)'],
    ['ss_pol', 'i', {intensityReport_polarization}, 'polarization component to extract after spectrum vs photon energy calculation: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['ss_mag', 'i', 1, 'magnetic field to be used for single-e spectrum vs photon energy calculation: 1- approximate, 2- accurate'],
    ['ss_fn', 's', 'res_spec_se.dat', 'file name for saving calculated single-e spectrum vs photon energy'],
    ['ss_pl', 's', '', 'plot the resulting single-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],

    #Multi-Electron Spectrum vs Photon Energy (taking into account e-beam emittance, energy spread and collection aperture size)
    ['sm', '', '', 'calculate multi-e spectrum vs photon energy', 'store_true'],
    ['sm_ei', 'f', {fluxReport_initialEnergy}, 'initial photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ef', 'f', {fluxReport_finalEnergy}, 'final photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ne', 'i', 10000, 'number of points vs photon energy for multi-e spectrum vs photon energy calculation'],
    ['sm_x', 'f', {fluxReport_horizontalPosition}, 'horizontal center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_rx', 'f', {fluxReport_horizontalApertureSize}, 'range of horizontal position / horizontal aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_nx', 'i', 1, 'number of points vs horizontal position for multi-e spectrum vs photon energy calculation'],
    ['sm_y', 'f', {fluxReport_verticalPosition}, 'vertical center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ry', 'f', {fluxReport_verticalApertureSize}, 'range of vertical position / vertical aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ny', 'i', 1, 'number of points vs vertical position for multi-e spectrum vs photon energy calculation'],
    ['sm_mag', 'i', 1, 'magnetic field to be used for calculation of multi-e spectrum spectrum or intensity distribution: 1- approximate, 2- accurate'],
    ['sm_hi', 'i', 1, 'initial UR spectral harmonic to be taken into accountfor multi-e spectrum vs photon energy calculation'],
    ['sm_hf', 'i', 15, 'final UR spectral harmonic to be taken into accountfor multi-e spectrum vs photon energy calculation'],
    ['sm_prl', 'f', {fluxReport_longitudinalPrecision}, 'longitudinal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_pra', 'f', {fluxReport_azimuthalPrecision}, 'azimuthal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_type', 'i', {fluxReport_fluxType}, 'calculate flux (=1) or flux per unit surface (=2)'],
    ['sm_pol', 'i', {fluxReport_polarization}, 'polarization component to extract after calculation of multi-e flux or intensity: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['sm_fn', 's', 'res_spec_me.dat', 'file name for saving calculated milti-e spectrum vs photon energy'],
    ['sm_pl', 's', '', 'plot the resulting spectrum-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],
    #to add options for the multi-e calculation from "accurate" magnetic field

    #Power Density Distribution vs horizontal and vertical position
    ['pw', '', '', 'calculate SR power density distribution', 'store_true'],
    ['pw_x', 'f', {powerDensityReport_horizontalPosition}, 'central horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_rx', 'f', {powerDensityReport_horizontalRange}, 'range of horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_nx', 'i', 100, 'number of points vs horizontal position for calculation of power density distribution'],
    ['pw_y', 'f', {powerDensityReport_verticalPosition}, 'central vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ry', 'f', {powerDensityReport_verticalRange}, 'range of vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ny', 'i', 100, 'number of points vs vertical position for calculation of power density distribution'],
    ['pw_pr', 'f', {powerDensityReport_precision}, 'precision factor for calculation of power density distribution'],
    ['pw_meth', 'i', {powerDensityReport_method}, 'power density computation method (1- "near field", 2- "far field")'],
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

    ['w_e', 'f', {initialIntensityReport_photonEnergy}, 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1., 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', {initialIntensityReport_horizontalPosition}, 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', {initialIntensityReport_horizontalRange}, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 100, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', {initialIntensityReport_verticalPosition}, 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', {initialIntensityReport_verticalRange}, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 100, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', {initialIntensityReport_sampleFactor}, 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', {initialIntensityReport_method}, 'method to use for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_prec', 'f', {initialIntensityReport_precision}, 'relative precision for calculation of intensity distribution vs horizontal and vertical position'],
    ['si_pol', 'i', {initialIntensityReport_polarization}, 'polarization component to extract after calculation of intensity distribution: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['si_type', 'i', {initialIntensityReport_characteristic}, 'type of a characteristic to be extracted after calculation of intensity distribution: 0- Single-Electron Intensity, 1- Multi-Electron Intensity, 2- Single-Electron Flux, 3- Multi-Electron Flux, 4- Single-Electron Radiation Phase, 5- Re(E): Real part of Single-Electron Electric Field, 6- Im(E): Imaginary part of Single-Electron Electric Field, 7- Single-Electron Intensity, integrated over Time or Photon Energy'],
    ['w_mag', 'i', 1, 'magnetic field to be used for calculation of intensity distribution vs horizontal and vertical position: 1- approximate, 2- accurate'],

    ['si_fn', 's', 'res_int_se.dat', 'file name for saving calculated single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position'],
    ['ws_fni', 's', 'res_int_pr_se.dat', 'file name for saving propagated single-e intensity distribution vs horizontal and vertical position'],
    ['ws_pl', 's', '', 'plot the resulting intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    ['wm_nm', 'i', 100000, 'number of macro-electrons (coherent wavefronts) for calculation of multi-electron wavefront propagation'],
    ['wm_na', 'i', 5, 'number of macro-electrons (coherent wavefronts) to average on each node for parallel (MPI-based) calculation of multi-electron wavefront propagation'],
    ['wm_ns', 'i', 5, 'saving periodicity (in terms of macro-electrons / coherent wavefronts) for intermediate intensity at multi-electron wavefront propagation calculation'],
    ['wm_ch', 'i', 0, 'type of a characteristic to be extracted after calculation of multi-electron wavefront propagation: #0- intensity (s0); 1- four Stokes components; 2- mutual intensity cut vs x; 3- mutual intensity cut vs y'],
    ['wm_ap', 'i', 0, 'switch specifying representation of the resulting Stokes parameters: coordinate (0) or angular (1)'],
    ['wm_x0', 'f', 0, 'horizontal center position for mutual intensity cut calculation'],
    ['wm_y0', 'f', 0, 'vertical center position for mutual intensity cut calculation'],
    ['wm_ei', 'i', 0, 'integration over photon energy is required (1) or not (0); if the integration is required, the limits are taken from w_e, w_ef'],
    ['wm_rm', 'i', 1, 'method for generation of pseudo-random numbers for e-beam phase-space integration: 1- standard pseudo-random number generator, 2- Halton sequences, 3- LPtau sequences (to be implemented)'],
    ['wm_fni', 's', 'res_int_pr_me.dat', 'file name for saving propagated multi-e intensity distribution vs horizontal and vertical position'],

    #to add options
    ['op_r', 'f', {beamlineFirstElementPosition}, 'longitudinal position of the first optical element [m]'],
]

def get_srw_params():
    return varParam

def get_beamline_optics():
    {beamlineOptics}

'''

def _propagation_params(prop):
    res = '    pp.append(['
    for i in range(len(prop)):
        v = int(prop[i]) if i in (0, 1, 3, 4) else float(prop[i])
        res += str(v)
        if (i != len(prop) - 1):
            res += ', '
    res += '])\n'
    return res

def generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    propagation = models['propagation']
    res = '''
    el = []
    pp = []
'''
    prev = None

    for item in beamline:
        if prev:
            size = float(item['position']) - float(prev['position'])
            if size != 0:
                res += '    el.append(SRWLOptD({}))\n'.format(size)
                res += _propagation_params(propagation[str(prev['id'])][1])

        if item['type'] == 'aperture':
            res += '    el.append(SRWLOptA("{}", "a", {}, {}))\n'.format(
                _escape(item['shape'] if item.get('shape') else 'r'),
                _float(item, 'horizontalSize', 1000),
                _float(item, 'verticalSize', 1000))
            res += _propagation_params(propagation[str(item['id'])][0])
        elif item['type'] == 'crl':
            res += '    el.append(srwl_opt_setup_CRL({}, {}, {}, {}, {}, {}, {}, {}, {}, 0, 0))\n'.format(
                _escape(item['focalPlane']),
                _float(item, 'refractiveIndex'),
                _float(item, 'attenuationLength'),
                _escape(item['shape']),
                _float(item, 'horizontalApertureSize', 1000),
                _float(item, 'verticalApertureSize', 1000),
                _float(item, 'radius'),
                int(item['numberOfLenses']),
                _float(item,'wallThickness'))
            res += _propagation_params(propagation[str(item['id'])][0])
        elif item['type'] == 'lens':
            res += '    el.append(SRWLOptL({}, {}))\n'.format(
                _float(item, 'horizontalFocalLength'),
                _float(item, 'verticalFocalLength'))
            res += _propagation_params(propagation[str(item['id'])][0])
        elif item['type'] == 'mirror':
            res += '    ifnHDM = "mirror_1d.dat"\n'
            res += '    hProfDataHDM = srwl_uti_read_data_cols(ifnHDM, "\\\\t", 0, 1)\n'
            res += '    el.append(srwl_opt_setup_surf_height_1d(hProfDataHDM, "{}", _ang={}, _amp_coef={}, _nx=1000, _ny=200, _size_x={}, _size_y={}))\n'.format(
                _escape(item['orientation']),
                _float(item, 'grazingAngle', 1000),
                _float(item, 'heightAmplification'),
                _float(item, 'horizontalTransverseSize', 1000),
                _float(item, 'verticalTransverseSize', 1000))
            res += _propagation_params(propagation[str(item['id'])][0])
        elif item['type'] == 'obstacle':
            res += '    el.append(SRWLOptA("{}", "o", {}, {}))\n'.format(
                _escape(item['shape'] if item.get('shape') else 'r'),
                _float(item, 'horizontalSize', 1000),
                _float(item, 'verticalSize', 1000))
            res += _propagation_params(propagation[str(item['id'])][0])
        elif item['type'] == 'watch':
            if len(beamline) == 1:
                res += '    el.append(SRWLOptD({}))\n'.format(1.0e-16)
                res += _propagation_params(propagation[str(item['id'])][0])
            if last_id and last_id == int(item['id']):
                break
        prev = item
        res += '\n'

    # final propagation parameters
    res += _propagation_params(models['postPropagation'])
    res += '    return SRWLOptC(el, pp)\n'
    return res

def run_all_text():
    return '''
def run_all_reports():
    import srwl_bl
    v = srwl_bl.srwl_uti_parse_options(get_srw_params())
    v.ss = True
    v.ss_pl = 'e'
    v.sm = True
    v.sm_pl = 'e'
    v.pw = True
    v.pw_pl = 'xy'
    v.si = True
    v.ws = True
    v.ws_pl = 'xy'
    op = get_beamline_optics()
    srwl_bl.SRWLBeamline(v.name).calc_all(v, op)

run_all_reports()
'''

def _escape(v):
    return re.sub(r'[ ()\.]', '', str(v))

def _float(item, field, scale=1):
    return float(item[field]) / scale
