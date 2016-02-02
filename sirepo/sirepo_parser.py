import ast
import json
import os
import pprint

import requests


def get_json(json_url):
    return json.loads(requests.get(json_url).text)


static_url = 'https://raw.githubusercontent.com/radiasoft/sirepo/master/sirepo/package_data/static'
static_js_url = static_url + '/js'
static_json_url = static_url + '/json'


def sirepo_parser(content):
    """
    The function tries to read .py configuration files for SRW and returns a JSON dictionary with gathered data.
    Only standard file formats are supported at the moment: http://alpha.sirepo.com/srw#/simulations.
    The function uses Abstract Syntax Trees (AST) - https://greentreesnakes.readthedocs.org/en/latest/index.html.
    Other useful links:
        - http://stackoverflow.com/questions/768634/parse-a-py-file-read-the-ast-modify-it-then-write-back-the-modified-source-c
        - http://svn.python.org/view/python/trunk/Demo/parser/unparse.py?view=markup
        - https://docs.python.org/2/library/ast.html#module-ast
        - https://github.com/python-rope/rope
        - http://pythoscope.org/
        - http://eli.thegreenplace.net/2009/11/28/python-internals-working-with-python-asts/
        - http://blaag.haard.se/Using-the-AST-to-hack-constants-into-Python/
        - http://gabrielelanaro.github.io/blog/2014/12/12/extract-docstrings.html

    :param infile: input .py file.
    :return srwblParam: the list describing SRW parameters.
    :return appParam: the list with beam parameters.
    :return el: the list with elements of the beamline.
    :return pp: the list of propagation parameters.
    """

    el = []
    pp = []
    srwblParam = None
    appParam = None

    # if os.path.isfile(infile):
    #     with open(infile, 'r') as f:
    #         content = f.read()
    # "if True:" to preserve indent from original source
    if True:
        if True:
            tree = ast.parse(content)

            for i in range(len(tree.body)):
                # Find assignments of the lists 'srwblParam' and 'appParam':
                try:
                    varname = ast.Str(tree.body[i].targets).s[0].id
                    if varname == 'srwblParam':
                        srwblParam = ast.literal_eval(tree.body[i].value)
                    elif varname == 'appParam':
                        appParam = ast.literal_eval(tree.body[i].value)
                except:
                    pass

                try:
                    if tree.body[i].name == 'get_beamline_optics':
                        func_id = i
                except:
                    pass

            # Get info from get_beamline_optics() function - 'el' and 'pp' lists:
            for i in range(len(tree.body[func_id].body)):
                try:
                    list_name = tree.body[func_id].body[i].value.func.value.id
                    if list_name == 'el':
                        obj = tree.body[func_id].body[i].value.args[0]
                        srw_func = obj.func.attr

                        values = []
                        for j in range(len(obj.args)):
                            if hasattr(obj.args[j], 'n'):
                                values.append(obj.args[j].n)
                            elif hasattr(obj.args[j], 's'):
                                values.append(obj.args[j].s)

                        try:
                            if srw_func == 'srwl_opt_setup_surf_height_1d':
                                values = {}

                                # --- Begin of processing of the mirror file ---
                                values['heightProfileFile'] = None

                                # 1) hProfDataHDM = srwlib.srwl_uti_read_data_cols(ifnHDM, "\t", 0, 1)
                                ifnHDM_argument = None
                                for j in range(10):
                                    current_line = i - (j + 1)
                                    try:
                                        hProfDataHDM_assigned = tree.body[func_id].body[current_line].targets[0].id
                                        if hProfDataHDM_assigned == obj.args[0].id:
                                            ifnHDM_argument = tree.body[func_id].body[current_line].value.args[0].id
                                            break
                                    except:
                                        pass

                                # 2) ifnHDM = "mirror_1d.dat"
                                ifnHDM_assigned = None
                                ifnHDM_file = None
                                for j in range(10):
                                    current_line2 = current_line - (j + 1)
                                    try:
                                        ifnHDM_assigned = tree.body[func_id].body[current_line2].targets[0].id
                                        if ifnHDM_assigned == ifnHDM_argument:
                                            ifnHDM_file = tree.body[func_id].body[current_line2].value.s
                                            break
                                    except:
                                        pass

                                if ifnHDM_file:
                                    values['heightProfileFile'] = ifnHDM_file
                                # --- End of processing of the mirror file ---

                                for kw in obj.keywords:
                                    if kw.value.__class__.__name__ == 'Str':
                                        values[kw.arg] = kw.value.s
                                    elif kw.value.__class__.__name__ == 'Num':
                                        values[kw.arg] = kw.value.n
                                    else:
                                        pass

                                if '_dim' not in values.keys():
                                    if obj.args[1].__class__.__name__ == 'Str':
                                        values['_dim'] = obj.args[1].s
                                    elif obj.args[1].__class__.__name__ == 'Num':
                                        values['_dim'] = obj.args[1].n

                        except:
                            pass

                    elif list_name == 'pp':
                        obj = tree.body[func_id].body[i].value.args[0].elts
                        srw_func = None

                        values = []
                        for j in range(len(obj)):
                            if hasattr(obj[j], 'n'):
                                values.append(obj[j].n)
                            elif hasattr(obj[j], 's'):
                                values.append(obj[j].s)

                    else:
                        srw_func = ''
                        values = ''

                    if list_name == 'el':
                        el.append((srw_func, values))
                    elif list_name == 'pp':
                        pp.append(values)

                except:
                    pass

    return srwblParam, appParam, el, pp


# Convert a list of lists to an object:
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


class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


def get_default_drift():
    """The function parses srw.js file to find the default values for drift propagation parameters, which can be
    sometimes missed in the exported .py files (when distance = 0), but should be presented in .json files.

    :return default_drift_prop: found list as a string.
    """

    try:
        file_content = requests.get(static_js_url + '/srw.js').text
    except:
        file_content = u''

    default_drift_prop = u'[0, 0, 1, 1, 0, 1.0, 1.0, 1.0, 1.0]'

    try:  # open(file_name, 'r') as f:
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


def get_beamline_element(el, idx, title, elem_type, position):
    data = {}

    data[u'id'] = idx
    data[u'type'] = unicode(elem_type)
    data[u'title'] = unicode(title)  # u'S0',
    data[u'position'] = position  # 20.5

    if elem_type == 'aperture':
        data[u'shape'] = unicode(el[1][0])  # u'r'
        data[u'horizontalOffset'] = el[1][4]  # 0
        data[u'verticalOffset'] = el[1][5]  # 0,
        data[u'horizontalSize'] = el[1][2] * 1e3  # 0.2
        data[u'verticalSize'] = el[1][3] * 1e3  # 1

    elif elem_type == 'mirror':
        data[u'grazingAngle'] = el[1]['_ang'] * 1.e3  # u'3.1415926',
        data[u'heightAmplification'] = el[1]['_amp_coef']  # u'1',
        data[u'heightProfileFile'] = el[1]['heightProfileFile']  # u'mirror_1d.dat',
        data[u'horizontalTransverseSize'] = el[1]['_size_x'] * 1.e3  # u'0.94',
        data[u'orientation'] = unicode(el[1]['_dim'])  # u'x'
        data[u'verticalTransverseSize'] = el[1]['_size_y'] * 1.e3  # u'1'

    elif elem_type == 'crl':
        data[u'attenuationLength'] = el[1][2]  # u'7.31294e-03'
        data[u'focalPlane'] = el[1][0]
        data[u'horizontalApertureSize'] = el[1][4] * 1.e3  # u'1'
        data[u'numberOfLenses'] = el[1][7]  # u'1'
        data[u'radius'] = el[1][6]  # u'1.5e-03'
        data[u'refractiveIndex'] = el[1][1]  # u'4.20756805e-06'
        data[u'shape'] = el[1][3]  # 1
        data[u'verticalApertureSize'] = el[1][5] * 1.e3  # u'2.4'
        data[u'wallThickness'] = el[1][8]  # u'80.e-06'

    elif elem_type == 'lens':
        data[u'horizontalFocalLength'] = el[1][0]  # u'3.24479',
        data[u'horizontalOffset'] = el[1][2]  # 0
        data[u'verticalFocalLength'] = el[1][1]  # u'1.e+23'
        data[u'verticalOffset'] = el[1][3]  # 0

    else:
        pass

    return data


def get_beamline(el, init_distance=20.0):
    """The function creates a beamline from the provided list of elements parsed by AST.

    :param el: list containing properties of the beamline elements.
    :param init_distance: distance from the source to the first element (20.0 m by default).
    :return elements_list: list of all found beamline elements.
    """

    num_elements = len(el)

    elements_list = []

    # The dictionary to count the elements of different types:
    names = {
        'S': -1,
        'HDM': '',
        'CRL': 0,
        'KL': '',
        'KLA': '',
        'Sample': '',
    }

    positions = []  # a list with sequence of distances between elements
    positions_from_source = []  # a list with sequence of distances from source

    for i in range(num_elements):
        name = el[i][0]
        try:
            next_name = el[i + 1][0]
        except:
            next_name = None

        if name != 'SRWLOptD':  # or i == len(obj_arOpt) - 1:  # not drift
            # Check if the next element is drift, else put 0 distance:
            if next_name == 'SRWLOptD':
                positions.append(el[i + 1][1][0])
            else:
                positions.append(0.0)

    positions_from_source.append(init_distance)  # add distance to the first element
    for i in range(len(positions)):
        dist_from_source = init_distance + sum(positions[:i + 1])
        positions_from_source.append(dist_from_source)

    counter = 0

    for i in range(num_elements):
        name = el[i][0]
        if name != 'SRWLOptD' or i == len(el) - 1:  # drifts are not included in the list, except the last drift
            counter += 1

            key = ''
            elem_type = ''

            if name == 'SRWLOptA':
                key = 'S'
                names[key] += 1
                elem_type = 'aperture'

            elif name == 'srwl_opt_setup_surf_height_1d':  # mirror, no surface curvature
                key = 'HDM'
                elem_type = 'mirror'

            elif name == 'srwl_opt_setup_CRL':  # CRL
                key = 'CRL'
                names[key] += 1
                elem_type = 'crl'

            elif name == 'SRWLOptL':
                key = 'KL'
                elem_type = 'lens'

            if i == len(el) - 1:
                key = 'Sample'
                elem_type = 'watch'

            title = key + str(names[key])

            data = get_beamline_element(el[i], counter, title, elem_type, positions_from_source[counter - 1])

            elements_list.append(data)

    return elements_list


def get_propagation(el, pp, default_drift):
    prop_dict = {}
    counter = 0
    for i in range(len(pp) - 1):
        name = el[i][0]
        try:
            next_name = el[i + 1][0]
        except:
            next_name = None

        if name != 'SRWLOptD' or i == len(pp) - 2:  # drifts are not included in the list, except the last drift
            counter += 1
            prop_dict[unicode(str(counter))] = [pp[i]]

            if next_name == 'SRWLOptD':
                prop_dict[unicode(str(counter))].append(pp[i + 1])
            else:
                prop_dict[unicode(str(counter))].append(default_drift)

    return prop_dict


def parsed_dict(v, app, el, pp):
    """
    The function is to produce JSON-file with the parsed data.

    :param v:
    :param app:
    :param el:
    :param pp:
    :return python_dict:
    """

    def _get_gb(app):
        try:
            gaussianBeam = {
                u'energyPerPulse': app.gb_energy_per_pulse,  # u'0.001',
                u'polarization': app.gb_polarization,  # 1,
                u'rmsPulseDuration': app.gb_rms_pulse_duration * 1e12,  # 0.1,
                u'rmsSizeX': app.gb_rms_size_x * 1e6,  # u'9.78723',
                u'rmsSizeY': app.gb_rms_size_y * 1e6,  # u'9.78723',
                u'waistAngleX': app.gb_waist_angle_x,  # 0,
                u'waistAngleY': app.gb_waist_angle_y,  # 0,
                u'waistX': app.gb_waist_x,  # 0,
                u'waistY': app.gb_waist_y,  # 0,
                u'waistZ': app.gb_waist_z,  # 0,
            }
        except:
            gaussianBeam = {
                u'energyPerPulse': None,
                u'polarization': None,
                u'rmsPulseDuration': None,
                u'rmsSizeX': None,
                u'rmsSizeY': None,
                u'waistAngleX': None,
                u'waistAngleY': None,
                u'waistX': None,
                u'waistY': None,
                u'waistZ': None,
            }

        return gaussianBeam

    def _get_source_type(app):
        if hasattr(app, 'source_type'):
            source_type = app.source_type
        elif hasattr(app, 'mag_type'):
            source_type = app.mag_type
        else:
            source_type = u''

        return source_type

    python_dict = {
        u'models': {
            u'beamline': get_beamline(el, v.op_r),
            u'electronBeam': {
                u'beamSelector': unicode(v.ebm_nm),  # u'NSLS-II Low Beta Day 1',
                u'current': v.ebm_i,  # 0.5,
                u'energy': app.ueb_e,  # 3,
                u'energyDeviation': v.ebm_de,  # 0,
                u'horizontalAlpha': app.ueb_alpha_x,  # 0,
                u'horizontalBeta': app.ueb_beta_x,  # 2.02,
                u'horizontalDispersion': app.ueb_eta_x,  # 0,
                u'horizontalDispersionDerivative': app.ueb_eta_x_pr,  # 0,
                u'horizontalEmittance': app.ueb_emit_x * 1e9,  # 0.9,
                u'horizontalPosition': v.ebm_x,  # 0,
                u'isReadOnly': True,
                u'name': unicode(v.ebm_nm),  # u'NSLS-II Low Beta Day 1',
                u'rmsSpread': app.ueb_sig_e,  # 0.00089,
                u'verticalAlpha': app.ueb_alpha_y,  # 0,
                u'verticalBeta': app.ueb_beta_y,  # 1.06,
                u'verticalDispersion': app.ueb_eta_y,  # 0,
                u'verticalDispersionDerivative': app.ueb_eta_y_pr,  # 0,
                u'verticalEmittance': app.ueb_emit_y * 1e9,  # 0.008,
                u'verticalPosition': v.ebm_y,  # 0
            },
            u'electronBeams': [],
            u'fluxReport': {
                u'azimuthalPrecision': v.sm_pra,  # 1,
                u'distanceFromSource': v.op_r,  # 20.5,
                u'finalEnergy': v.sm_ef,  # 20000,
                u'fluxType': v.sm_type,  # 1,
                u'horizontalApertureSize': v.sm_rx * 1e3,  # u'1',
                u'horizontalPosition': v.sm_x,  # 0,
                u'initialEnergy': v.sm_ei,  # u'100',
                u'longitudinalPrecision': v.sm_prl,  # 1,
                u'photonEnergyPointCount': v.sm_ne,  # 10000,
                u'polarization': v.sm_pol,  # 6,
                u'verticalApertureSize': v.sm_ry * 1e3,  # u'1',
                u'verticalPosition': v.sm_y,  # 0,
            },
            u'gaussianBeam': _get_gb(app),
            u'initialIntensityReport': {
                u'characteristic': v.si_type,  # 0,
                u'horizontalPosition': v.w_x,  # 0,
                u'horizontalRange': v.w_rx * 1e3,  # u'0.4',
                u'polarization': v.si_pol,  # 6,
                u'precision': v.w_prec,  # Static values in .py template: 0.01,
                u'verticalPosition': v.w_y,  # 0,
                u'verticalRange': v.w_ry * 1e3,  # u'0.6',
            },
            u'intensityReport': {
                u'distanceFromSource': v.op_r,  # 20.5,
                u'finalEnergy': v.ss_ef,  # u'20000',
                u'horizontalPosition': v.ss_x,  # u'0',
                u'initialEnergy': v.ss_ei,  # u'100',
                u'photonEnergyPointCount': v.ss_ne,  # 10000,
                u'polarization': v.ss_pol,  # 6,
                u'precision': v.ss_prec,  # 0.01,
                u'verticalPosition': v.ss_y,  # 0,
            },
            u'multipole': {
                u'distribution': unicode(app.mp_distribution),  # u'n',
                u'field': app.mp_field,  # 0.4,
                u'length': app.mp_len,  # 3,
                u'order': app.mp_order,  # 1,
            },
            u'postPropagation': pp[-1],  # [0, 0, u'1', 0, 0, u'0.3', u'2', u'0.5', u'1'],
            u'powerDensityReport': {
                u'distanceFromSource': v.op_r,  # 20.5,
                u'horizontalPointCount': v.pw_nx,  # 100,
                u'horizontalPosition': v.pw_x,  # u'0',
                u'horizontalRange': v.pw_rx * 1e3,  # u'15',
                u'method': v.pw_meth,  # 1,
                u'precision': v.pw_pr,  # u'1',
                u'verticalPointCount': v.pw_ny,  # 100,
                u'verticalPosition': v.pw_y,  # u'0',
                u'verticalRange': v.pw_ry * 1e3,  # u'15',
            },
            u'propagation': get_propagation(el, pp, get_default_drift()),
            u'simulation': {
                u'facility': unicode(v.name.split()[0]),  # u'NSLS-II',
                u'horizontalPointCount': v.w_nx,  # 100,
                u'isExample': 0,  # u'1',
                u'name': unicode(v.name),  # u'NSLS-II CHX beamline',
                u'photonEnergy': v.w_e,  # u'9000',
                u'sampleFactor': v.w_smpf,  # 1,
                u'simulationId': None,  # u'1YA8lSnj',
                u'sourceType': unicode(_get_source_type(app)),  # u'u',
                u'verticalPointCount': v.w_ny,  # 100
            },
            # TODO: Ask RadiaSoft if it's correct to take everything from defaults for this report:
            u'sourceIntensityReport': get_json(static_json_url + '/srw-default.json')['models'][
                'sourceIntensityReport'],
            u'undulator': {
                u'horizontalAmplitude': v.und_bx,  # u'0',
                u'horizontalInitialPhase': v.und_phx,  # 0,
                u'horizontalSymmetry': v.und_sx,  # 1,
                u'length': v.und_len,  # u'3',
                u'longitudinalPosition': v.und_zc,  # 0,
                u'period': v.und_per * 1e3,  # u'20',
                u'verticalAmplitude': v.und_by,  # u'0.88770981',
                u'verticalInitialPhase': v.und_phy,  # 0,
                u'verticalSymmetry': v.und_sy,  # -1
            },
            # TODO: Ask RadiaSoft how to process it:
            u'watchpointReport11': {
                u'characteristic': None,  # 0,
                u'horizontalPosition': None,  # 0,
                u'horizontalRange': None,  # u'0.4',
                u'polarization': None,  # 6,
                u'precision': None,  # 0.01,
                u'verticalPosition': None,  # 0,
                u'verticalRange': None,  # u'0.6',
            },
        },
        u'report': u'',  # u'powerDensityReport',
        u'simulationType': u'srw',
        u'version': unicode(get_json(static_json_url + '/schema-common.json')['version']),  # u'20160120',
    }

    return python_dict


def main(py_file, debug=False):

    with open(py_file, 'r') as f:
        srwblParam, appParam, el, pp = sirepo_parser(f.read())

    args = list2dict(srwblParam)
    v = Struct(**args)

    args = list2dict(appParam)
    app = Struct(**args)

    python_dict = parsed_dict(v, app, el, pp)

    if debug:
        pprint.pprint(python_dict)

    save_file = 'parsed_sirepo.json'
    with open(save_file, 'w') as f:
        json.dump(
            python_dict,
            f,
            sort_keys=True,
            indent=4,
            separators=(',', ': '),
        )
        print '\n\tJSON output is saved in <%s>.' % save_file

    return


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Parse Sirepo-generated .py file.')
    parser.add_argument('-f', '--file', dest='py_file', help='input Python file.')
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='enable debug information.')

    args = parser.parse_args()
    py_file = args.py_file
    debug = args.debug

    if py_file and os.path.isfile(py_file):
        sys.exit(main(py_file, debug))
