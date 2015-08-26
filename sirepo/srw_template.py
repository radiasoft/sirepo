import re

TEMPLATE = '''

import srwlib
import srwl_bl

srwblParam = [

    ['name', 's', '{simulation_name}', 'simulation name'],

#---Data Folder
    ['fdir', 's', '', 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', '{electronBeam_name}', 'standard electron beam name'],
    ['ebm_nms', 's', '', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', {electronBeam_current}, 'electron beam current [A]'],
    ['ebm_de', 'f', {electronBeam_energyDeviation}, 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', {electronBeam_horizontalPosition}, 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', {electronBeam_verticalPosition}, 'electron beam initial average vertical position [m]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', {electronBeamInitialDrift}, 'electron beam longitudinal drift [m] to be performed before a required calculation'],

#---Undulator
    ['und_bx', 'f', {undulator_horizontalAmplitude}, 'undulator horizontal peak magnetic field [T]'],
    ['und_by', 'f', {undulator_verticalAmplitude}, 'undulator vertical peak magnetic field [T]'],
    ['und_phx', 'f', {undulator_horizontalInitialPhase}, 'initial phase of the horizontal magnetic field [rad]'],
    ['und_phy', 'f', {undulator_verticalInitialPhase}, 'initial phase of the vertical magnetic field [rad]'],
    ['und_b2e', '', '', 'estimate undulator fundamental photon energy (in [eV]) for the amplitude of sinusoidal magnetic field defined by und_b or und_bx, und_by', 'store_true'],
    ['und_e2b', '', '', 'estimate undulator field amplitude (in [T]) for the photon energy defined by w_e', 'store_true'],
    ['und_per', 'f', {undulator_period}, 'undulator period [m]'],
    ['und_len', 'f', {undulator_length}, 'undulator length [m]'],
    ['und_zc', 'f', 0., 'undulator center longitudinal position [m]'],
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
    ['ss_meth', 'i', {energyCalculationMethod}, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
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
    ['w_meth', 'i', {energyCalculationMethod}, 'method to use for calculation of intensity distribution vs horizontal and vertical position'],
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

appParam = [
    ['mag_type', 's', '{simulation_sourceType}', 'source type, (u) undulator, (m) multipole'],
#---Multipole
    ['mp_field', 'f', {multipole_field}, 'field parameter [T] for dipole, [T/m] for quadrupole (negative means defocusing for x), [T/m^2] for sextupole, [T/m^3] for octupole'],
    ['mp_order', 'i', 1, 'multipole order 1 for dipole, 2 for quadrupoole, 3 for sextupole, 4 for octupole'],
    ['mp_distribution', 's', '{multipole_distribution}', 'normal (n) or skew (s)'],
    ['mp_len', 'f', {multipole_length}, 'effective length [m]'],
    ['mp_zc', 'f', 0., 'multipole center longitudinal position [m]'],
#---User Defined Electron Beam
    ['ueb', 'i', {userDefinedElectronBeam}, 'Use user defined beam'],
    ['ueb_e', 'f', {electronBeam_energy}, 'energy [GeV]'],
    ['ueb_sig_e', 'f', {electronBeam_rmsSpread}, 'RMS energy spread'],
    ['ueb_emit_x', 'f', {electronBeam_horizontalEmittance}, 'horizontal emittance [m]'],
    ['ueb_beta_x', 'f', {electronBeam_horizontalBeta}, 'horizontal beta-function [m]'],
    ['ueb_alpha_x', 'f', {electronBeam_horizontalAlpha}, 'horizontal alpha-function [rad]'],
    ['ueb_eta_x', 'f', {electronBeam_horizontalDispersion}, 'horizontal dispersion function [m]'],
    ['ueb_eta_x_pr', 'f', {electronBeam_horizontalDispersionDerivative}, 'horizontal dispersion function derivative [rad]'],
    ['ueb_emit_y', 'f', {electronBeam_verticalEmittance}, 'vertical emittance [m]'],
    ['ueb_beta_y', 'f', {electronBeam_verticalBeta}, 'vertical beta-function [m]'],
    ['ueb_alpha_y', 'f', {electronBeam_verticalAlpha}, 'vertical alpha-function [rad]'],
    ['ueb_eta_y', 'f', {electronBeam_verticalDispersion}, 'vertical dispersion function [m]'],
    ['ueb_eta_y_pr', 'f', {electronBeam_verticalDispersionDerivative}, 'vertical dispersion function derivative [rad]'],
]

def setup_magnetic_field(v):
    appV = srwl_bl.srwl_uti_parse_options(appParam)

    if appV.ueb:
        srwl_bl._USER_DEFINED_EBEAM = srwl_bl.SRWLPartBeam()
        srwl_bl._USER_DEFINED_EBEAM.from_Twiss(_e=appV.ueb_e, _sig_e=appV.ueb_sig_e, _emit_x=appV.ueb_emit_x, _beta_x=appV.ueb_beta_x, _alpha_x=appV.ueb_alpha_x, _eta_x=appV.ueb_eta_x, _eta_x_pr=appV.ueb_eta_x_pr, _emit_y=appV.ueb_emit_y, _beta_y=appV.ueb_beta_y, _alpha_y=appV.ueb_alpha_y, _eta_y=appV.ueb_eta_y, _eta_y_pr=appV.ueb_eta_y_pr)

    if appV.mag_type == 'u':
        v.und_b = 1
        return None
    mag = srwlib.SRWLMagFldC();
    mag.arXc.append(0)
    mag.arYc.append(0)
    if appV.mag_type == 'm':
        mag.arMagFld.append(srwlib.SRWLMagFldM(appV.mp_field, appV.mp_order, appV.mp_distribution, appV.mp_len))
        mag.arZc.append(appV.mp_zc)
    return mag

def get_srw_params():
    return srwblParam

def get_app_params():
    return appParam

def get_beamline_optics():
    {beamlineOptics}

# monkey patch SRWLBeamline.set_e_beam() to allow a user defined ebeam when called from calc_all()
original_method = srwl_bl.SRWLBeamline.set_e_beam

def patched_srwl_bl_set_e_beam(self, **kwargs):
    if hasattr(srwl_bl, '_USER_DEFINED_EBEAM'):
        kwargs['_e_beam_name'] = ''
        kwargs['_e_beam'] = srwl_bl._USER_DEFINED_EBEAM
    return original_method(self, **kwargs)

srwl_bl.SRWLBeamline.set_e_beam = patched_srwl_bl_set_e_beam

'''


def generate_parameters_file(data, schema):
    if 'report' in data and re.search('watchpointReport', data['report']):
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][data['report']]
    _validate_data(data, schema)
    last_id = None
    if 'report' in data:
        m = re.search('watchpointReport(\d+)', data['report'])
        if m:
            last_id = int(m.group(1))
    v = _flatten_data(data['models'], {})
    v['beamlineOptics'] = _generate_beamline_optics(data['models'], last_id)
    beamline = data['models']['beamline']
    v['beamlineFirstElementPosition'] = beamline[0]['position'] if len(beamline) else 20
    # initial drift = 1/2 undulator length + 2 periods
    source_type = data['models']['simulation']['sourceType']
    drift = 0
    if source_type == 'u':
        drift = -0.5 * data['models']['undulator']['length'] - 2 * data['models']['undulator']['period']
    elif source_type == 'm':
        #TODO(pjm): allow this to be set in UI?
        drift = 0;
    elif source_type == 's':
        drift = 0
    else:
        raise Exception('invalid magneticField type: {}'.format(source_type))
    v['electronBeamInitialDrift'] = drift
    # 1: auto-undulator 2: auto-wiggler
    v['energyCalculationMethod'] = 1 if source_type == 'u' else 2
    v['userDefinedElectronBeam'] = 1
    if 'isReadOnly' in data['models']['electronBeam'] and data['models']['electronBeam']['isReadOnly']:
        v['userDefinedElectronBeam'] = 0
    return TEMPLATE.format(**v).decode('unicode-escape')


def run_all_text():
    return '''
def run_all_reports():
    v = srwl_bl.srwl_uti_parse_options(get_srw_params())
    mag = setup_magnetic_field(v)
    v.ss = True
    v.ss_pl = 'e'
    if isinstance(mag, srwlib.SRWLMagFldU):
        v.sm = True
        v.sm_pl = 'e'
    v.pw = True
    v.pw_pl = 'xy'
    v.si = True
    v.ws = True
    v.ws_pl = 'xy'
    op = get_beamline_optics()
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)

run_all_reports()
'''

def _escape(v):
    return re.sub("['()\.]", '', str(v))


def _flatten_data(d, res, prefix=''):
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            _flatten_data(v, res, prefix + k + '_')
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = v
    return res


def _beamline_element(template, item, fields, propagation):
    return '    el.append({})\n{}'.format(
        template.format(*map(lambda x: item[x], fields)),
        _propagation_params(propagation[str(item['id'])][0]),
    )


def _generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    propagation = models['propagation']
    res = '''
    el = []
    pp = []
'''
    prev = None
    has_item = False

    for item in beamline:
        if prev:
            has_item = True
            size = item['position'] - prev['position']
            if size != 0:
                res += '    el.append(srwlib.SRWLOptD({}))\n'.format(size)
                res += _propagation_params(propagation[str(prev['id'])][1])
        if item['type'] == 'aperture':
            res += _beamline_element(
                'srwlib.SRWLOptA("{}", "a", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'crl':
            res += _beamline_element(
                'srwlib.srwl_opt_setup_CRL({}, {}, {}, {}, {}, {}, {}, {}, {}, 0, 0)',
                item,
                ['focalPlane', 'refractiveIndex', 'attenuationLength', 'shape', 'horizontalApertureSize', 'verticalApertureSize', 'radius', 'numberOfLenses', 'wallThickness'],
                propagation)
        elif item['type'] == 'lens':
            res += _beamline_element(
                'srwlib.SRWLOptL({}, {}, {}, {})',
                item,
                ['horizontalFocalLength', 'verticalFocalLength', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'mirror':
            res += '    ifnHDM = "mirror_1d.dat"\n'
            res += '    hProfDataHDM = srwlib.srwl_uti_read_data_cols(ifnHDM, "\\\\t", 0, 1)\n'
            res += _beamline_element(
                'srwlib.srwl_opt_setup_surf_height_1d(hProfDataHDM, "{}", _ang={}, _amp_coef={}, _nx=1000, _ny=200, _size_x={}, _size_y={})',
                item,
                ['orientation', 'grazingAngle', 'heightAmplification', 'horizontalTransverseSize', 'verticalTransverseSize'],
                propagation)
        elif item['type'] == 'obstacle':
            res += _beamline_element(
                'srwlib.SRWLOptA("{}", "o", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'watch':
            if not has_item:
                res += '    el.append(srwlib.SRWLOptD({}))\n'.format(1.0e-16)
                res += _propagation_params(propagation[str(item['id'])][0])
            if last_id and last_id == int(item['id']):
                break
        prev = item
        res += '\n'

    # final propagation parameters
    res += _propagation_params(models['postPropagation'])
    res += '    return srwlib.SRWLOptC(el, pp)\n'
    return res


def _parse_enums(enum_schema):
    res = {}
    for k in enum_schema:
        res[k] = {}
        for v in enum_schema[k]:
            res[k][v[0]] = True
    return res

def _propagation_params(prop):
    res = '    pp.append(['
    for i in range(len(prop)):
        res += str(prop[i])
        if (i != len(prop) - 1):
            res += ', '
    res += '])\n'
    return res

def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = _parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            _validate_model(data['models'][k], schema['model'][k], enum_info)
    for m in data['models']['beamline']:
        _validate_model(m, schema['model'][m['type']], enum_info)
    for item_id in data['models']['propagation']:
        _validate_propagation(data['models']['propagation'][item_id][0])
        _validate_propagation(data['models']['propagation'][item_id][1])
    _validate_propagation(data['models']['postPropagation'])

def _validate_model(model_data, model_schema, enum_info):
    for k in model_schema:
        label = model_schema[k][0]
        field_type = model_schema[k][1]
        value = model_data[k]
        if field_type in enum_info:
            if not enum_info[field_type][str(value)]:
                raise Exception('invalid enum value: {}'.format(value))
        elif field_type == 'Float':
            if not value:
                value = 0
            v = float(value)
            if re.search('\[m(m|rad)\]', label):
                v /= 1000
            elif re.search('\[nm\]', label):
                v /= 1e09;
            model_data[k] = v
        elif field_type == 'Integer':
            if not value:
                value = 0
            model_data[k] = int(value)
        elif field_type == 'BeamList' or field_type == 'File' or field_type == 'String':
            model_data[k] = _escape(value)
        else:
            raise Exception('unknown field type: {}'.format(field_type))

def _validate_propagation(prop):
    for i in range(len(prop)):
        prop[i] = int(prop[i]) if i in (0, 1, 3, 4) else float(prop[i])
