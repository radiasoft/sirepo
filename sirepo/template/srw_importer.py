# -*- coding: utf-8 -*-
u"""
This script is to parse SRW Python scripts and to produce JSON-file with the parsed data.
It's highly dependent on the external Sirepo/SRW libraries and is written to allow parsing of the .py files using
SRW objects.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkresource
from pykern import pkrunpy
from pykern.pkdebug import pkdlog, pkdexc, pkdp
import ast
import inspect
import py.path
import re
import srwl_bl

_JS_DIR = py.path.local(pkresource.filename('static/js'))


class SRWParser(object):
    def __init__(self, script, lib_dir, user_filename, arguments, optics_func_name='set_optics'):
        self.lib_dir = py.path.local(lib_dir)
        m = pkrunpy.run_path_as_module(script)
        if arguments:
            import shlex
            arguments = shlex.split(arguments)
        self.var_param = srwl_bl.srwl_uti_parse_options(m.varParam, use_sys_argv=False, args=arguments)
        self.replace_mirror_files()
        self.replace_image_files()
        try:
            self.optics = getattr(m, optics_func_name)(self.var_param)
        except ValueError as e:
            if re.search('could not convert string to float', e.message):
                self.replace_mirror_files('mirror_2d.dat')
                self.optics = getattr(m, optics_func_name)(self.var_param)
        self.data = _parsed_dict(self.var_param, self.optics)
        self.data.models.simulation.name = _name(user_filename)

    def replace_mirror_files(self, mirror_file='mirror_1d.dat'):
        for key in self.var_param.__dict__.keys():
            if key == 'fdir':
                self.var_param.__dict__[key] = str(self.lib_dir)
            if re.search(r'\_ofn$', key):
                self.var_param.__dict__[key] = ''
            if re.search(r'\_(h|i)fn$', key):
                if getattr(self.var_param, key) != '' and getattr(self.var_param, key) != 'None':
                    self.var_param.__dict__[key] = str(self.lib_dir.join(mirror_file))

    def replace_image_files(self, image_file='sample.tif'):
        for key in self.var_param.__dict__.keys():
            if key.find('op_sample') >= 0:
                if getattr(self.var_param, key) != '':
                    self.var_param.__dict__[key] = str(self.lib_dir.join(image_file))


class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


def import_python(code, tmp_dir, lib_dir, user_filename=None, arguments=None):
    """Converts script_text into json and stores as new simulation.

    Avoids too much data back to the user in the event of an error.
    This could be a potential security issue, because the script
    could be used to probe the system.

    Args:
        simulation_type (str): always "srw", but used to find lib dir
        code (str): Python code that runs SRW
        user_filename (str): uploaded file name for log
        arguments (str): argv to be passed to script

    Returns:
        dict: simulation data
    """
    script = None

    # Patch for the mirror profile for the exported .py file from Sirepo:
    code = _patch_mirror_profile(code, lib_dir)

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
            return o.data
    except Exception as e:
        lineno = script and _find_line_in_trace(script)
        # Avoid
        pkdlog(
            'Error: {}; exception={}; script={}; filename={}; stack:\n{}',
            e.message,
            e,
            script,
            user_filename,
            pkdexc(),
        )
        e = str(e)[:50]
        raise ValueError(
            'Error on line {}: {}'.format(lineno, e) if lineno
            else 'Error: {}'.format(e))


# Mapping all the values to a dictionary:
def _beamline_element(obj, idx, title, elem_type, position):
    data = pkcollections.Dict()

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
        # Fixed values in srw.js:
        data['heightAmplification'] = 1
        data['heightProfileFile'] = None
        data['orientation'] = 'x'

        data['material'] = 'Unknown'
        data['h'] = '1'
        data['k'] = '1'
        data['l'] = '1'
        try:
            data['energy'] = obj.aux_energy
        except Exception:
            data['energy'] = None
        try:
            data['grazingAngle'] = obj.aux_ang_dif_pl
        except Exception:
            data['grazingAngle'] = 0.0
        data['asymmetryAngle'] = obj.angAs
        data['rotationAngle'] = 0.0
        data['crystalThickness'] = obj.tc
        data['dSpacing'] = obj.dSp
        data['psi0r'] = obj.psi0r
        data['psi0i'] = obj.psi0i
        data['psiHr'] = obj.psiHr
        data['psiHi'] = obj.psiHi
        data['psiHBr'] = obj.psiHbr
        data['psiHBi'] = obj.psiHbi
        data['nvx'] = obj.nvx
        data['nvy'] = obj.nvy
        data['nvz'] = obj.nvz
        data['tvx'] = obj.tvx
        data['tvy'] = obj.tvy

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

    elif elem_type == 'fiber':
        data['method'] = 'server'
        data['externalMaterial'] = 'User-defined'
        data['coreMaterial'] = 'User-defined'
        keys = ['focalPlane', 'externalRefractiveIndex', 'coreRefractiveIndex', 'externalAttenuationLength',
                'coreAttenuationLength', 'externalDiameter', 'coreDiameter', 'horizontalCenterPosition',
                'verticalCenterPosition']
        for key in keys:
            data[key] = obj.input_parms[key]

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
        for key in ['grazingAngle', 'horizontalTransverseSize', 'verticalTransverseSize']:
            data[key] *= 1000.0

        data['type'] = 'mirror'
        data['heightProfileFile'] = 'mirror_1d.dat' if elem_type == 'mirror' else 'mirror_2d.dat'

    elif elem_type == 'sample':
        data['imageFile'] = 'sample.tif'
        data['material'] = 'User-defined'
        data['method'] = 'server'
        keys = ['resolution', 'thickness', 'refractiveIndex', 'attenuationLength']
        for key in keys:
            if type(obj.input_parms) == tuple:
                data[key] = obj.input_parms[0][key]
            else:
                data[key] = obj.input_parms[key]
        data['resolution'] *= 1e9
        data['thickness'] *= 1e6

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

    elif elem_type == 'zonePlate':
        data['numberOfZones'] = obj.nZones
        data['outerRadius'] = obj.rn * 1e3
        data['thickness'] = obj.thick * 1e6
        data['method'] = 'server'
        data['mainMaterial'] = 'User-defined'
        data['mainRefractiveIndex'] = obj.delta1
        data['mainAttenuationLength'] = obj.atLen1
        data['complementaryMaterial'] = 'User-defined'
        data['complementaryRefractiveIndex'] = obj.delta2
        data['complementaryAttenuationLength'] = obj.atLen2
        data['horizontalOffset'] = obj.x
        data['verticalOffset'] = obj.y

    elif elem_type == 'watch':
        pass

    else:
        raise Exception('Element type <{}> does not exist.'.format(elem_type))

    return data


def _get_beamline(obj_arOpt, init_distance=20.0):
    """The function creates a beamline from the provided object and/or AST tree.

    :param obj_arOpt: SRW object containing properties of the beamline elements.
    :param init_distance: distance from the source to the first element (20.0 m by default).
    :return elements_list: list of all found beamline elements.
    """

    num_elements = len(obj_arOpt)

    elements_list = []

    # The dictionary to count the elements of different types:
    names = pkcollections.Dict({
        'S': 0,
        'O': 0,
        'HDM': 0,
        'CRL': 0,
        'KL': 0,
        'KLA': 0,
        'AUX': 0,
        'M': 0,  # mirror
        'G': 0,  # grating
        'ZP': 0, # zone plate
        'Crystal': 0,
        'Fiber': 0,
        'Watch': '',
        'Sample': '',
    })

    positions = []  # a list of dictionaries with sequence of distances between elements

    d_src = init_distance
    counter = 0
    for i in range(num_elements):
        name = obj_arOpt[i].__class__.__name__
        try:
            next_name = obj_arOpt[i + 1].__class__.__name__
        except Exception:
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
                if type(obj_arOpt[i].input_parms) == tuple:
                    elem_type = obj_arOpt[i].input_parms[0]['type']
                else:
                    elem_type = obj_arOpt[i].input_parms['type']

                if elem_type in ['mirror', 'mirror2d']:
                    key = 'HDM'

                elif elem_type == 'crl':  # CRL
                    key = 'CRL'

                elif elem_type == 'cyl_fiber':
                    elem_type = 'fiber'
                    key = 'Fiber'

                elif elem_type == 'sample':
                    key = 'Sample'

            elif name == 'SRWLOptZP':
                key = 'ZP'
                elem_type = 'zonePlate'

            # Last element is Sample:
            if name == 'SRWLOptD' and (i + 1) == num_elements:
                key = 'Watch'
                elem_type = 'watch'

            try:
                names[key] += 1
            except Exception:
                pass

            title = key + str(names[key])

            positions.append(pkcollections.Dict({
                'id': counter,
                'object': obj_arOpt[i],
                'elem_class': name,
                'elem_type': elem_type,
                'title': title,
                'dist': d,
                'dist_source': float(str(d_src)),
            }))

    for i in range(len(positions)):
        data = _beamline_element(
            positions[i]['object'],
            positions[i]['id'],
            positions[i]['title'],
            positions[i]['elem_type'],
            positions[i]['dist_source']
        )
        elements_list.append(data)

    return elements_list


def _get_default_drift():
    """The function parses srw.js file to find the default values for drift propagation parameters, which can be
    sometimes missed in the exported .py files (when distance = 0), but should be presented in .json files.

    :return default_drift_prop: found list as a string.
    """

    try:
        with open(_JS_DIR + '/srw.js') as f:
            file_content = f.read()
    except Exception:
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
    except Exception:
        pass

    default_drift_prop = ast.literal_eval(default_drift_prop)

    return default_drift_prop


def _get_propagation(op):
    prop_dict = pkcollections.Dict()
    counter = 0
    for i in range(len(op.arProp) - 1):
        name = op.arOpt[i].__class__.__name__
        try:
            next_name = op.arOpt[i + 1].__class__.__name__
        except Exception:
            next_name = None

        if (name != 'SRWLOptD') or \
                (name == 'SRWLOptD' and next_name == 'SRWLOptD') or \
                ((i + 1) == len(op.arProp) - 1):  # exclude last drift
            counter += 1
            prop_dict[str(counter)] = [op.arProp[i]]
            if next_name == 'SRWLOptD':
                prop_dict[str(counter)].append(op.arProp[i + 1])
            else:
                prop_dict[str(counter)].append(_get_default_drift())

    return prop_dict


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


def _list2dict(data_list):
    """
    The function converts list of lists to a dictionary with keys from 1st elements and values from 3rd elements.

    :param data_list: list of SRW parameters (e.g., 'appParam' in Sirepo's *.py files).
    :return out_dict: dictionary with all parameters.
    """

    out_dict = pkcollections.Dict()

    for i in range(len(data_list)):
        out_dict[data_list[i][0]] = data_list[i][2]

    return out_dict


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
    return m.group(1) if m else user_filename


def _parsed_dict(v, op):
    import sirepo.template.srw
    std_options = Struct(**_list2dict(srwl_bl.srwl_uti_std_options()))

    beamline_elements = _get_beamline(op.arOpt, v.op_r)

    # Since the rotation angle cannot be passed from SRW object, we update the angle here:
    beamline_elements = _update_crystals(beamline_elements, v)

    def _default_value(parm, obj, std, def_val=None):
        if not hasattr(obj, parm):
            try:
                return getattr(std, parm)
            except Exception:
                if def_val is not None:
                    return def_val
                else:
                    return ''
        try:
            return getattr(obj, parm)
        except Exception:
            if def_val is not None:
                return def_val
            else:
                return ''

    # This dictionary will is used for both initial intensity report and for watch point:
    initialIntensityReport = pkcollections.Dict({
        'characteristic': v.si_type,
        'fieldUnits': 1,
        'polarization': v.si_pol,
        'precision': v.w_prec,
        'sampleFactor': 0,
    })

    predefined_beams = sirepo.template.srw.get_predefined_beams()

    # Default electron beam:
    if (hasattr(v, 'source_type') and v.source_type == 'u') or (hasattr(v, 'ebm_nm') and v.gbm_pen == 0):
        source_type = 'u'
        if v.ebm_nms == 'Day1':
            v.ebm_nms = 'Day 1'
        full_beam_name = '{}{}'.format(v.ebm_nm, v.ebm_nms)
        electronBeam = pkcollections.Dict()
        for b in predefined_beams:
            if b['name'] == full_beam_name:
                electronBeam = b
                electronBeam['beamSelector'] = full_beam_name
                break
        if not electronBeam:
            electronBeam = pkcollections.Dict({
                'beamSelector': full_beam_name,
                'current': v.ebm_i,
                'energy': _default_value('ebm_e', v, std_options, 3.0),
                'energyDeviation': _default_value('ebm_de', v, std_options, 0.0),
                'horizontalAlpha': _default_value('ebm_alphax', v, std_options, 0.0),
                'horizontalBeta': _default_value('ebm_betay', v, std_options, 2.02),
                'horizontalDispersion': _default_value('ebm_etax', v, std_options, 0.0),
                'horizontalDispersionDerivative': _default_value('ebm_etaxp', v, std_options, 0.0),
                'horizontalEmittance': _default_value('ebm_emx', v, std_options, 9e-10) * 1e9,
                'horizontalPosition': v.ebm_x,
                'isReadOnly': False,
                'name': full_beam_name,
                'rmsSpread': _default_value('ebm_ens', v, std_options, 0.00089),
                'verticalAlpha': _default_value('ebm_alphay', v, std_options, 0.0),
                'verticalBeta': _default_value('ebm_betay', v, std_options, 1.06),
                'verticalDispersion': _default_value('ebm_etay', v, std_options, 0.0),
                'verticalDispersionDerivative': _default_value('ebm_etaxp', v, std_options, 0.0),
                'verticalEmittance': _default_value('ebm_emy', v, std_options, 8e-12) * 1e9,
                'verticalPosition': v.ebm_y,
            })

        undulator = pkcollections.Dict({
            'horizontalAmplitude': _default_value('und_bx', v, std_options, 0.0),
            'horizontalInitialPhase': _default_value('und_phx', v, std_options, 0.0),
            'horizontalSymmetry': str(int(_default_value('und_sx', v, std_options, 1.0))),
            'length': _default_value('und_len', v, std_options, 1.5),
            'longitudinalPosition': _default_value('und_zc', v, std_options, 1.305),
            'period': _default_value('und_per', v, std_options, 0.021) * 1e3,
            'verticalAmplitude': _default_value('und_by', v, std_options, 0.88770981) if hasattr(v, 'und_by') else _default_value('und_b', v, std_options, 0.88770981),
            'verticalInitialPhase': _default_value('und_phy', v, std_options, 0.0),
            'verticalSymmetry': str(int(_default_value('und_sy', v, std_options, -1))),
        })

        gaussianBeam = pkcollections.Dict({
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
        })

    else:
        source_type = 'g'
        electronBeam = pkcollections.Dict()
        default_ebeam_name = 'NSLS-II Low Beta Final'
        for beam in predefined_beams:
            if beam['name'] == default_ebeam_name:
                electronBeam = beam
                electronBeam['beamSelector'] = default_ebeam_name
                break
        if not electronBeam:
            raise ValueError('Electron beam is not set during import')
        undulator = pkcollections.Dict({
            "horizontalAmplitude": "0",
            "horizontalInitialPhase": 0,
            "horizontalSymmetry": 1,
            "length": 3,
            "longitudinalPosition": 0,
            "period": "20",
            "undulatorParameter": 1.65776086,
            "verticalAmplitude": "0.88770981",
            "verticalInitialPhase": 0,
            "verticalSymmetry": -1,
        })

        gaussianBeam = pkcollections.Dict({
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
        })

    python_dict = pkcollections.Dict({
        'models': pkcollections.Dict({
            'beamline': beamline_elements,
            'electronBeam': electronBeam,
            'electronBeams': [],
            'fluxReport': pkcollections.Dict({
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
            }),
            'initialIntensityReport': initialIntensityReport,
            'intensityReport': pkcollections.Dict({
                'distanceFromSource': v.op_r,
                'fieldUnits': 1,
                'finalEnergy': v.ss_ef,
                'horizontalPosition': v.ss_x,
                'initialEnergy': v.ss_ei,
                'photonEnergyPointCount': v.ss_ne,
                'polarization': v.ss_pol,
                'precision': v.ss_prec,
                'verticalPosition': v.ss_y,
            }),
            'multiElectronAnimation': pkcollections.Dict({
                'horizontalPosition': 0,
                'horizontalRange': v.w_rx * 1e3,
                'stokesParameter': '0',
                'verticalPosition': 0,
                'verticalRange': v.w_ry * 1e3,
            }),
            'multipole': pkcollections.Dict({
                'distribution': 'n',
                'field': 0,
                'length': 0,
                'order': 1,
            }),
            'postPropagation': op.arProp[-1],
            'powerDensityReport': pkcollections.Dict({
                'distanceFromSource': v.op_r,
                'horizontalPointCount': v.pw_nx,
                'horizontalPosition': v.pw_x,
                'horizontalRange': v.pw_rx * 1e3,
                'method': v.pw_meth,
                'precision': v.pw_pr,
                'verticalPointCount': v.pw_ny,
                'verticalPosition': v.pw_y,
                'verticalRange': v.pw_ry * 1e3,
            }),
            'propagation': _get_propagation(op),
            'simulation': pkcollections.Dict({
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
            }),
            'sourceIntensityReport': pkcollections.Dict({
                'characteristic': v.si_type,  # 0,
                'distanceFromSource': v.op_r,
                'fieldUnits': 1,
                'polarization': v.si_pol,
            }),
            'undulator': undulator,
            'gaussianBeam': gaussianBeam,
        }),
        'simulationType': 'srw',
        'version': '',
    })

    # Format the key name to be consistent with Sirepo:
    for i in range(len(beamline_elements)):
        if beamline_elements[i]['type'] == 'watch':
            idx = beamline_elements[i]['id']
            python_dict['models']['watchpointReport{}'.format(idx)] = initialIntensityReport

    return python_dict


def _patch_mirror_profile(code, lib_dir, mirror_file='mirror_1d.dat'):
    """Patch for the mirror profile for the exported .py file from Sirepo"""
    import sirepo.template.srw
    # old format mirror names
    var_names = ['Cryst', 'ElMirror', 'Mirror', 'SphMirror', 'TorMirror']
    code_list = code.split('\n')
    for var_name in var_names:
        if var_name in ['Mirror']:
            final_mirror_file = '"{}/{}"'.format(lib_dir, mirror_file)
        else:
            final_mirror_file = None
        var_name = 'ifn' + var_name
        for i in range(len(code_list)):
            if re.search('^(\s*)' + var_name + '(\d*)(\s*)=(\s*)(.*\.dat\w*)(\s*)', code_list[i]):
                full_var_name = code_list[i].strip().split('=')[0].strip()
                code_list[i] = code_list[i].replace(
                    full_var_name,
                    '{} = {}  # '.format(full_var_name, final_mirror_file)
                )
    code = '\n'.join(code_list)
    return code


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
            except Exception:
                crystal_id = 1

            try:  # update rotation angle
                data[i]['rotationAngle'] = getattr(v, 'op_DCM_ac{}'.format(crystal_id))
            except Exception:
                pass

            if not data[i]['energy']:
                try:  # update energy if an old srwlib.py is used
                    data[i]['energy'] = v.op_DCM_e
                except Exception:
                    data[i]['energy'] = v.w_e

    return data
