"""
This script is to parse SRW Python scripts and to produce JSON-file with the parsed data.
It's highly dependent on the external Sirepo/SRW libraries and is written to allow parsing of the .py files using
SRW objects.
"""
from __future__ import absolute_import, division, print_function

import ast
import inspect
import json
import re
import traceback

import py
import requests
from pykern import pkio
from pykern import pkrunpy
from pykern.pkdebug import pkdp
from srwl_bl import srwl_uti_parse_options
from srwl_bl import srwl_uti_std_options

try:
    import cPickle as pickle
except:
    import pickle


def import_python(code, tmp_dir, lib_dir, user_filename=None, arguments=None):
    """Converts script_text into json and stores as new simulation.

    Avoids too much data back to the user in the event of an error.
    This could be a potential security issue, because the script
    could be used to probe the system.

    Args:
        simulation_type (str): always "srw", but used to find lib dir
        code (str): Python code that runs SRW
        user_filename (str): uploaded file name for log

    Returns:
        error: string containing error or None
        dict: simulation data
    """
    error = 'Import failed: error unknown'
    script = None
    try:
        with pkio.save_chdir(tmp_dir):
            # This string won't show up anywhere
            script = pkio.write_text('in.py', code)
            o = SRWParser(
                script,
                lib_dir=py.path.local(lib_dir),
                user_filename=user_filename,
                arguments=arguments,
            )
            return None, o.data
    except Exception as e:
        lineno = _find_line_in_trace(script) if script else None
        # Avoid
        pkdp(
            'Error: {}; exception={}; script={}; filename={}; stack:\n{}',
            error,
            e,
            script,
            user_filename,
            traceback.format_exc(),
        )
        error = 'Error on line {}: {}'.format(lineno or '?', str(e)[:50])
    return error, None


def get_json(json_url):
    return json.loads(requests.get(json_url).text)


static_url = 'https://raw.githubusercontent.com/radiasoft/sirepo/master/sirepo/package_data/static'
static_js_url = static_url + '/js'
static_json_url = static_url + '/json'


def list2dict(data_list):
    """
    The function converts list of lists to a dictionary with keys from 1st elements and values from 3rd elements.

    :param data_list: list of SRW parameters (e.g., 'appParam' in Sirepo's *.py files).
    :return out_dict: dictionary with all parameters.
    """

    out_dict = {}

    for i in range(len(data_list)):
        out_dict[data_list[i][0]] = data_list[i][2]

    return out_dict


class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


# For sourceIntensityReport:
try:
    import py.path
    from pykern import pkresource

    static_dir = py.path.local(pkresource.filename('static'))
except:
    static_dir = '/home/vagrant/src/radiasoft/sirepo/sirepo/package_data/static'

static_js_dir = static_dir + '/js'
static_json_dir = static_dir + '/json'


def get_default_drift():
    """The function parses srw.js file to find the default values for drift propagation parameters, which can be
    sometimes missed in the exported .py files (when distance = 0), but should be presented in .json files.

    :return default_drift_prop: found list as a string.
    """

    try:
        file_content = requests.get(static_js_url + '/srw.js').text
    except:
        file_content = ''

    default_drift_prop = '[0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0]'

    try:
        content = file_content.split('\n')
        for i in range(len(content)):
            if content[i].find('function defaultDriftPropagationParams()') >= 0:
                # Find 'return' statement:
                for j in range(10):
                    '''
                        function defaultDriftPropagationParams() {
                            return [0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0];
                        }
                    '''
                    if content[i + j].find('return') >= 0:
                        default_drift_prop = content[i + j].replace('return ', '').replace(';', '').strip()
                        break
                break
    except:
        pass

    default_drift_prop = ast.literal_eval(default_drift_prop)

    return default_drift_prop


# Mapping all the values to a dictionary:
def beamline_element(obj, idx, title, elem_type, position):
    data = dict()

    data['id'] = idx
    data['type'] = elem_type
    data['title'] = title
    data['position'] = position

    if elem_type in ['aperture', 'obstacle']:
        data['shape'] = obj.shape

        data['horizontalOffset'] = obj.x
        data['verticalOffset'] = obj.y
        data['horizontalSize'] = obj.Dx * 1e3
        data['verticalSize'] = obj.Dy * 1e3

    elif elem_type == 'crl':
        keys = ['attenuationLength', 'focalPlane', 'horizontalApertureSize', 'numberOfLenses', 'radius',
                'refractiveIndex', 'shape', 'verticalApertureSize', 'wallThickness']

        for key in keys:
            data[key] = obj.input_parms[key]

        # Should be multiplied by 1000.0:
        for key in ['horizontalApertureSize', 'verticalApertureSize']:
            data[key] *= 1000.0

    elif elem_type == 'crystal':
        try:
            data['energy'] = obj.energy
        except:
            data['energy'] = None
        data['rotationAngle'] = 0.0
        data['dSpacing'] = obj.dSp
        data['psi0r'] = obj.psi0r
        data['psi0i'] = obj.psi0i
        data['psi_hr'] = obj.psiHr
        data['psi_hi'] = obj.psiHi
        data['psi_hbr'] = obj.psiHbr
        data['psi_hbi'] = obj.psiHbi
        data['crystalThickness'] = obj.tc
        data['asymmetryAngle'] = obj.angAs

    elif elem_type == 'ellipsoidMirror':
        # Fixed values in srw.js:
        data['heightAmplification'] = 1
        data['heightProfileFile'] = None
        data['orientation'] = 'x'

        data['firstFocusLength'] = obj.p
        data['focalLength'] = obj.q
        data['grazingAngle'] = obj.angGraz * 1e3
        data['normalVectorX'] = obj.nvx
        data['normalVectorY'] = obj.nvy
        data['normalVectorZ'] = obj.nvz
        data['sagittalSize'] = obj.ds
        data['tangentialSize'] = obj.dt
        data['tangentialVectorX'] = obj.tvx
        data['tangentialVectorY'] = obj.tvy

    elif elem_type == 'grating':
        # Fixed values in srw.js:
        data['grazingAngle'] = 12.9555790185373

        data['diffractionOrder'] = obj.m
        data['grooveDensity0'] = obj.grDen
        data['grooveDensity1'] = obj.grDen1
        data['grooveDensity2'] = obj.grDen2
        data['grooveDensity3'] = obj.grDen3
        data['grooveDensity4'] = obj.grDen4
        data['normalVectorX'] = obj.mirSub.nvx
        data['normalVectorY'] = obj.mirSub.nvy
        data['normalVectorZ'] = obj.mirSub.nvz
        data['sagittalSize'] = obj.mirSub.ds
        data['tangentialSize'] = obj.mirSub.dt
        data['tangentialVectorX'] = obj.mirSub.tvx
        data['tangentialVectorY'] = obj.mirSub.tvy

    elif elem_type == 'lens':
        data['horizontalFocalLength'] = obj.Fx
        data['horizontalOffset'] = obj.x
        data['verticalFocalLength'] = obj.Fy
        data['verticalOffset'] = obj.y

    elif elem_type in ['mirror', 'mirror2d']:
        keys = ['grazingAngle', 'heightAmplification', 'heightProfileFile', 'horizontalTransverseSize',
                'orientation', 'verticalTransverseSize']
        for key in keys:
            if type(obj.input_parms) == tuple:
                data[key] = obj.input_parms[0][key]
            else:
                data[key] = obj.input_parms[key]

        # Should be multiplied by 1000.0:
        for key in ['horizontalTransverseSize', 'verticalTransverseSize']:
            data[key] *= 1000.0

        data['heightProfileFile'] = 'mirror_1d.dat' if elem_type == 'mirror' else 'mirror_2d.dat'
        # TODO(mrakitin): currently 2D mirror profiles are not supported, need to add support later.
        data['type'] = 'mirror'

    elif elem_type == 'sphericalMirror':
        # Fixed values in srw.js:
        data['grazingAngle'] = 13.9626000172
        data['heightAmplification'] = 1
        data['heightProfileFile'] = None
        data['orientation'] = 'x'

        data['normalVectorX'] = obj.nvx
        data['normalVectorY'] = obj.nvy
        data['normalVectorZ'] = obj.nvz
        data['radius'] = obj.rad
        data['sagittalSize'] = obj.ds
        data['tangentialSize'] = obj.dt
        data['tangentialVectorX'] = obj.tvx
        data['tangentialVectorY'] = obj.tvy

    elif elem_type == 'watch':
        pass

    else:
        raise Exception('Element type <{}> does not exist.'.format(elem_type))

    return data


def get_beamline(obj_arOpt, init_distance=20.0):
    """The function creates a beamline from the provided object and/or AST tree.

    :param obj_arOpt: SRW object containing properties of the beamline elements.
    :param init_distance: distance from the source to the first element (20.0 m by default).
    :return elements_list: list of all found beamline elements.
    """

    num_elements = len(obj_arOpt)

    elements_list = []

    # The dictionary to count the elements of different types:
    names = {
        'S': 0,
        'O': 0,
        'HDM': 0,
        'CRL': 0,
        'KL': 0,
        'KLA': 0,
        'AUX': 0,
        'M': 0,  # mirror
        'G': 0,  # grating
        'Crystal': 0,
        'Sample': '',
    }

    positions = []  # a list of dictionaries with sequence of distances between elements

    d_src = init_distance
    counter = 0
    for i in range(num_elements):
        name = obj_arOpt[i].__class__.__name__
        try:
            next_name = obj_arOpt[i + 1].__class__.__name__
        except:
            next_name = None

        if name == 'SRWLOptD':
            d = obj_arOpt[i].L
        else:
            d = 0.0
        d_src += d

        if (len(positions) == 0) or \
                (name != 'SRWLOptD') or \
                (name == 'SRWLOptD' and next_name == 'SRWLOptD') or \
                (name == 'SRWLOptD' and (i + 1) == num_elements):

            counter += 1

            elem_type = ''

            if name == 'SRWLOptA':
                if obj_arOpt[i].ap_or_ob == 'a':
                    elem_type = 'aperture'
                    key = 'S'
                else:
                    elem_type = 'obstacle'
                    key = 'O'

            elif name == 'SRWLOptCryst':
                key = 'Crystal'
                elem_type = 'crystal'

            elif name == 'SRWLOptD':
                key = 'AUX'
                elem_type = 'watch'

            elif name == 'SRWLOptG':
                key = 'G'
                elem_type = 'grating'

            elif name == 'SRWLOptL':
                key = 'KL'
                elem_type = 'lens'

            elif name == 'SRWLOptMirEl':
                key = 'M'
                elem_type = 'ellipsoidMirror'

            elif name == 'SRWLOptMirSph':
                key = 'M'
                elem_type = 'sphericalMirror'

            elif name == 'SRWLOptT':
                # Check the type based on focal lengths of the element:
                if type(obj_arOpt[i].input_parms) == tuple:
                    elem_type = obj_arOpt[i].input_parms[0]['type']
                else:
                    elem_type = obj_arOpt[i].input_parms['type']

                if elem_type in ['mirror', 'mirror2d']:
                    key = 'HDM'

                elif elem_type == 'crl':  # CRL
                    key = 'CRL'

            # Last element is Sample:
            if name == 'SRWLOptD' and (i + 1) == num_elements:
                key = 'Sample'
                elem_type = 'watch'

            try:
                names[key] += 1
            except:
                pass

            title = key + str(names[key])

            positions.append({
                'id': counter,
                'object': obj_arOpt[i],
                'elem_class': name,
                'elem_type': elem_type,
                'title': title,
                'dist': d,
                'dist_source': float(str(d_src)),
            })

    for i in range(len(positions)):
        data = beamline_element(
            positions[i]['object'],
            positions[i]['id'],
            positions[i]['title'],
            positions[i]['elem_type'],
            positions[i]['dist_source']
        )
        elements_list.append(data)

    return elements_list


def get_propagation(op):
    prop_dict = {}
    counter = 0
    for i in range(len(op.arProp) - 1):
        name = op.arOpt[i].__class__.__name__
        try:
            next_name = op.arOpt[i + 1].__class__.__name__
        except:
            next_name = None

        if (name != 'SRWLOptD') or \
                (name == 'SRWLOptD' and next_name == 'SRWLOptD') or \
                ((i + 1) == len(op.arProp) - 1):  # exclude last drift
            counter += 1
            prop_dict[str(counter)] = [op.arProp[i]]
            if next_name == 'SRWLOptD':
                prop_dict[str(counter)].append(op.arProp[i + 1])
            else:
                prop_dict[str(counter)].append(get_default_drift())

    return prop_dict


def _update_crystals(data, v):
    """Update rotation angle from the parameters value.

    Args:
        data: list of beamline elements from get_beamline() function.
        v: object containing all variables.

    Returns:
        data: updated list.
    """

    for i in range(len(data)):
        if data[i]['type'] == 'crystal':
            try:  # get crystal #
                crystal_id = int(data[i]['title'].replace('Crystal', ''))
            except:
                crystal_id = 1

            try:  # update rotation angle
                data[i]['rotationAngle'] = getattr(v, 'op_DCM_ac{}'.format(crystal_id))
            except:
                pass

            if not data[i]['energy']:
                try:  # update energy if an old srwlib.py is used
                    data[i]['energy'] = v.op_DCM_e
                except:
                    data[i]['energy'] = v.w_e

    return data


def parsed_dict(v, op):
    std_options = Struct(**list2dict(srwl_uti_std_options()))

    beamline_elements = get_beamline(op.arOpt, v.op_r)

    # Since the rotation angle cannot be passed from SRW object, we update the angle here:
    beamline_elements = _update_crystals(beamline_elements, v)

    def _default_value(parm, obj, std, def_val=None):
        if not hasattr(obj, parm):
            try:
                return getattr(std, parm)
            except:
                if def_val is not None:
                    return def_val
                else:
                    return ''
        try:
            return getattr(obj, parm)
        except:
            if def_val is not None:
                return def_val
            else:
                return ''

    # This dictionary will is used for both initial intensity report and for watch point:
    initialIntensityReport = {
        'characteristic': v.si_type,
        'fieldUnits': 2,
        'polarization': v.si_pol,
        'precision': v.w_prec,
        'sampleFactor': 0,
    }

    # Default electron beam:
    if hasattr(v, 'ebm_nm'):
        source_type = 'u'

        electronBeam = {
            'beamSelector': v.ebm_nm,
            'current': v.ebm_i,
            'energy': _default_value('ueb_e', v, std_options, 3.0),
            'energyDeviation': _default_value('ebm_de', v, std_options, 0.0),
            'horizontalAlpha': _default_value('ueb_alpha_x', v, std_options, 0.0),
            'horizontalBeta': _default_value('ueb_beta_x', v, std_options, 2.02),
            'horizontalDispersion': _default_value('ueb_eta_x', v, std_options, 0.0),
            'horizontalDispersionDerivative': _default_value('ueb_eta_x_pr', v, std_options, 0.0),
            'horizontalEmittance': _default_value('ueb_emit_x', v, std_options, 9e-10) * 1e9,
            'horizontalPosition': v.ebm_x,
            'isReadOnly': False,
            'name': v.ebm_nm,
            'rmsSpread': _default_value('ueb_sig_e', v, std_options, 0.00089),
            'verticalAlpha': _default_value('ueb_alpha_y', v, std_options, 0.0),
            'verticalBeta': _default_value('ueb_beta_y', v, std_options, 1.06),
            'verticalDispersion': _default_value('ueb_eta_y', v, std_options, 0.0),
            'verticalDispersionDerivative': _default_value('ueb_eta_y_pr', v, std_options, 0.0),
            'verticalEmittance': _default_value('ueb_emit_y', v, std_options, 8e-12) * 1e9,
            'verticalPosition': v.ebm_y,
        }

        undulator = {
            'horizontalAmplitude': _default_value('und_bx', v, std_options, 0.0),
            'horizontalInitialPhase': _default_value('und_phx', v, std_options, 0.0),
            'horizontalSymmetry': _default_value('und_sx', v, std_options, 1.0),
            'length': _default_value('und_len', v, std_options, 1.5),
            'longitudinalPosition': _default_value('und_zc', v, std_options, 1.305),
            'period': _default_value('und_per', v, std_options, 0.021) * 1e3,
            'verticalAmplitude': _default_value('und_by', v, std_options, 0.88770981),
            'verticalInitialPhase': _default_value('und_phy', v, std_options, 0.0),
            'verticalSymmetry': _default_value('und_sy', v, std_options, -1),
        }

        gaussianBeam = {
            'energyPerPulse': None,
            'polarization': 1,
            'rmsPulseDuration': None,
            'rmsSizeX': None,
            'rmsSizeY': None,
            'waistAngleX': None,
            'waistAngleY': None,
            'waistX': None,
            'waistY': None,
            'waistZ': None,
        }

    else:
        source_type = 'g'
        electronBeam = {
            'beamSelector': None,
            'current': None,
            'energy': None,
            'energyDeviation': None,
            'horizontalAlpha': None,
            'horizontalBeta': 1.0,
            'horizontalDispersion': None,
            'horizontalDispersionDerivative': None,
            'horizontalEmittance': None,
            'horizontalPosition': None,
            'isReadOnly': False,
            'name': None,
            'rmsSpread': None,
            'verticalAlpha': None,
            'verticalBeta': 1.0,
            'verticalDispersion': None,
            'verticalDispersionDerivative': None,
            'verticalEmittance': None,
            'verticalPosition': None,
        }
        undulator = {
            'horizontalAmplitude': None,
            'horizontalInitialPhase': None,
            'horizontalSymmetry': 1,
            'length': None,
            'longitudinalPosition': None,
            'period': None,
            'verticalAmplitude': None,
            'verticalInitialPhase': None,
            'verticalSymmetry': 1,
        }

        gaussianBeam = {
            'energyPerPulse': _default_value('gbm_pen', v, std_options),
            'polarization': _default_value('gbm_pol', v, std_options),
            'rmsPulseDuration': _default_value('gbm_st', v, std_options) * 1e12,
            'rmsSizeX': _default_value('gbm_sx', v, std_options) * 1e6,
            'rmsSizeY': _default_value('gbm_sy', v, std_options) * 1e6,
            'waistAngleX': _default_value('gbm_xp', v, std_options),
            'waistAngleY': _default_value('gbm_yp', v, std_options),
            'waistX': _default_value('gbm_x', v, std_options),
            'waistY': _default_value('gbm_y', v, std_options),
            'waistZ': _default_value('gbm_z', v, std_options),
        }

    python_dict = {
        'models': {
            'beamline': beamline_elements,
            'electronBeam': electronBeam,
            'electronBeams': [],
            'fluxReport': {
                'azimuthalPrecision': v.sm_pra,
                'distanceFromSource': v.op_r,
                'finalEnergy': v.sm_ef,
                'fluxType': v.sm_type,
                'horizontalApertureSize': v.sm_rx * 1e3,
                'horizontalPosition': v.sm_x,
                'initialEnergy': v.sm_ei,
                'longitudinalPrecision': v.sm_prl,
                'photonEnergyPointCount': v.sm_ne,
                'polarization': v.sm_pol,
                'verticalApertureSize': v.sm_ry * 1e3,
                'verticalPosition': v.sm_y,
            },
            'initialIntensityReport': initialIntensityReport,
            'intensityReport': {
                'distanceFromSource': v.op_r,
                'fieldUnits': 1,
                'finalEnergy': v.ss_ef,
                'horizontalPosition': v.ss_x,
                'initialEnergy': v.ss_ei,
                'photonEnergyPointCount': v.ss_ne,
                'polarization': v.ss_pol,
                'precision': v.ss_prec,
                'verticalPosition': v.ss_y,
            },
            'multiElectronAnimation': {
                'horizontalPosition': 0,
                'horizontalRange': v.w_rx * 1e3,
                'stokesParameter': '0',
                'verticalPosition': 0,
                'verticalRange': v.w_ry * 1e3,
            },
            'multipole': {
                'distribution': 'n',
                'field': 0,
                'length': 0,
                'order': 1,
            },
            'postPropagation': op.arProp[-1],
            'powerDensityReport': {
                'distanceFromSource': v.op_r,
                'horizontalPointCount': v.pw_nx,
                'horizontalPosition': v.pw_x,
                'horizontalRange': v.pw_rx * 1e3,
                'method': v.pw_meth,
                'precision': v.pw_pr,
                'verticalPointCount': v.pw_ny,
                'verticalPosition': v.pw_y,
                'verticalRange': v.pw_ry * 1e3,
            },
            'propagation': get_propagation(op),
            'simulation': {
                'facility': 'Import',
                'horizontalPointCount': v.w_nx,
                'horizontalPosition': v.w_x,
                'horizontalRange': v.w_rx * 1e3,
                'isExample': 0,
                'name': '',
                'photonEnergy': v.w_e,
                'sampleFactor': v.w_smpf,
                'samplingMethod': 1,
                'simulationId': '',
                'sourceType': source_type,
                'verticalPointCount': v.w_ny,
                'verticalPosition': v.w_y,
                'verticalRange': v.w_ry * 1e3,
            },
            'sourceIntensityReport': {
                'characteristic': v.si_type,  # 0,
                'distanceFromSource': v.op_r,
                'fieldUnits': 2,
                'polarization': v.si_pol,
            },
            'undulator': undulator,
            'gaussianBeam': gaussianBeam,
        },
        'report': '',
        'simulationType': 'srw',
        'version': '',
    }

    # Format the key name to be consistent with Sirepo:
    for i in range(len(beamline_elements)):
        if beamline_elements[i]['type'] == 'watch':
            idx = beamline_elements[i]['id']
            python_dict['models']['watchpointReport{}'.format(idx)] = initialIntensityReport

    return python_dict


class SRWParser(object):
    def __init__(self, script, lib_dir, user_filename, arguments):
        self.lib_dir = lib_dir
        self.initial_lib_dir = lib_dir
        self.list_of_files = None
        m = pkrunpy.run_path_as_module(script)
        varParam = getattr(m, 'varParam')
        if arguments:
            import shlex
            arguments = shlex.split(arguments)
        self.var_param = srwl_uti_parse_options(varParam, use_sys_argv=False, args=arguments)
        self.get_files()
        if self.initial_lib_dir:
            self.replace_files()
        try:
            self.optics = getattr(m, 'set_optics')(self.var_param)
        except ValueError as e:
            if re.search('could not convert string to float', e.message):
                self.replace_files('mirror_2d.dat')
                self.optics = getattr(m, 'set_optics')(self.var_param)

        self.data = parsed_dict(self.var_param, self.optics)
        self.data['models']['simulation']['name'] = _name(user_filename)

    def get_files(self):
        self.list_of_files = []
        for key in self.var_param.__dict__.keys():
            if key.find('_ifn') >= 0:
                self.list_of_files.append(self.var_param.__dict__[key])
            # TODO(robnagler) this directory has to be a constant; imports
            #   don't have control of their environment
            if key.find('fdir') >= 0:
                self.lib_dir = py.path.local(self.var_param.__dict__[key])

    def replace_files(self, mirror_file='mirror_1d.dat'):
        for key in self.var_param.__dict__.keys():
            if key.find('_ifn') >= 0:
                if getattr(self.var_param, key) != '':
                    self.var_param.__dict__[key] = mirror_file
            if key.find('fdir') >= 0:
                self.var_param.__dict__[key] = str(self.initial_lib_dir)
        self.get_files()


def _name(user_filename):
    """Parse base name from user_filename

    Can't assume the file separators will be understood so have to
    parse out the name manually.

    Will need to be uniquely named by sirepo.server, but not done
    yet.

    Args:
        user_filename (str): Passed in from browser

    Returns:
        str: suitable name
    """
    # crude but good enough for now.
    m = re.search(r'([^:/\\]+)\.\w+$', user_filename)
    res = m.group(1) if m else user_filename
    # res could technically
    return res + ' (imported)'


def _find_line_in_trace(script):
    """Parse the stack trace for the most recent error message

    Returns:
        int: first line number in trace that was called from the script
    """
    trace = None
    t = None
    f = None
    try:
        trace = inspect.trace()
        for t in reversed(trace):
            f = t[0]
            if py.path.local(f.f_code.co_filename) == script:
                return f.f_lineno
    finally:
        del trace
        del f
        del t
    return None
