# -*- coding: utf-8 -*-
u"""shadow execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import os.path
import py.path
import xraylib

#: Simulation type
SIM_TYPE = 'shadow'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)
_SHADOW_OUTPUT_FILE = 'shadow-output.dat'

_REPORT_STYLE_FIELDS = ['colorMap', 'notes', 'aspectRatio']

_CENTIMETER_FIELDS = {
    'electronBeam': ['sigmax', 'sigmaz', 'epsi_x', 'epsi_z', 'epsi_dx', 'epsi_dz'],
    'geometricSource': ['wxsou', 'wzsou', 'sigmax', 'sigmaz', 'wysou', 'sigmay'],
    'rayFilter': ['distance', 'x1', 'x2', 'z1', 'z2'],
    'aperture': ['position', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
    'crl': ['position', 'pilingThickness', 'rmirr', 'focalDistance', 'lensThickness', 'lensDiameter'],
    'obstacle': ['position', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
    'histogramReport': ['distanceFromSource'],
    'plotXYReport': ['distanceFromSource'],
    'mirror': ['position', 'halfWidthX1', 'halfWidthX2', 'halfLengthY1', 'halfLengthY2', 'externalOutlineMajorAxis', 'externalOutlineMinorAxis', 'internalOutlineMajorAxis', 'internalOutlineMinorAxis', 'ssour', 'simag', 'rmirr', 'r_maj', 'r_min', 'param', 'axmaj', 'axmin', 'ell_the', 'prereflDensity', 'mlayerSubstrateDensity', 'mlayerEvenSublayerDensity', 'mlayerOddSublayerDensity'],
    'crystal': ['position', 'halfWidthX1', 'halfWidthX2', 'halfLengthY1', 'halfLengthY2', 'externalOutlineMajorAxis', 'externalOutlineMinorAxis', 'internalOutlineMajorAxis', 'internalOutlineMinorAxis', 'ssour', 'simag', 'rmirr', 'r_maj', 'r_min', 'param', 'axmaj', 'axmin', 'ell_the', 'thickness', 'r_johansson'],
    'grating': ['position', 'halfWidthX1', 'halfWidthX2', 'halfLengthY1', 'halfLengthY2', 'externalOutlineMajorAxis', 'externalOutlineMinorAxis', 'internalOutlineMajorAxis', 'internalOutlineMinorAxis', 'ssour', 'simag', 'rmirr', 'r_maj', 'r_min', 'param', 'axmaj', 'axmin', 'ell_the', 'rulingDensity', 'rulingDensityCenter', 'rulingDensityPolynomial', 'holo_r1', 'holo_r2', 'dist_fan', 'rul_a1', 'rul_a2', 'rul_a3', 'rul_a4', 'hunt_h', 'hunt_l'],
    'watch': ['position'],
}

_FIELD_ALIAS = {
    'externalOutlineMajorAxis': 'rwidx2',
    'externalOutlineMinorAxis': 'rlen2',
    'halfLengthY1': 'rlen1',
    'halfLengthY2': 'rlen2',
    'halfWidthX1': 'rwidx1',
    'halfWidthX2': 'rwidx2',
    'horizontalOffset': 'cx_slit[0]',
    'horizontalSize': 'rx_slit[0]',
    'internalOutlineMajorAxis': 'rwidx1',
    'internalOutlineMinorAxis': 'rlen1',
    'rulingDensity': 'ruling',
    'rulingDensityCenter': 'ruling',
    'rulingDensityPolynomial': 'ruling',
    'singleEnergyValue': 'ph1',
    'verticalOffset': 'cz_slit[0]',
    'verticalSize': 'rz_slit[0]',
}

_WIGGLER_TRAJECTOR_FILENAME = 'xshwig.sha'


def fixup_old_data(data):
    if (
        float(data.fixup_old_version) < 20170703.000001
        and 'geometricSource' in data.models
    ):
        g = data.models.geometricSource
        x = g.cone_max
        g.cone_max = g.cone_min
        g.cone_min = x
    for m in [
            'initialIntensityReport',
            'plotXYReport',
    ]:
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)
    for m in data.models:
        if template_common.is_watchpoint(m):
            template_common.update_model_defaults(data.models[m], 'watchpointReport', _SCHEMA)
    template_common.organize_example(data)


def get_application_data(data):
    if data['method'] == 'validate_material':
        name = data['material_name']
        try:
            xraylib.CompoundParser(str(name))
            return {
                'material_name': name,
            }
        except Exception:
            return {
                'error': 'invalid material name',
            }
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, model, frame, **kwargs):
    filename = _SHADOW_OUTPUT_FILE
    with open(str(run_dir.join(filename))) as f:
        return filename, f.read(), 'application/octet-stream'


def lib_files(data, source_lib):
    return template_common.filename_to_path(_simulation_files(data), source_lib)


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    res = template_common.report_fields(data, r, _REPORT_STYLE_FIELDS) + [
        'bendingMagnet',
        'electronBeam',
        'geometricSource',
        'rayFilter',
        'simulation.istar1',
        'simulation.npoint',
        'simulation.sourceType',
        'sourceDivergence',
        'wiggler',
    ]
    if r == 'initialIntensityReport' and len(data['models']['beamline']):
        res.append([data['models']['beamline'][0]['position']])
    #TODO(pjm): only include items up to the current watchpoint
    if template_common.is_watchpoint(r):
        res.append('beamline')
    for f in template_common.lib_files(data):
        res.append(f.mtime())
    return res


def python_source_for_model(data, model):
    beamline = data['models']['beamline']
    watch_id = None
    for b in beamline:
        if b['type'] == 'watch':
            watch_id = b['id']
    if watch_id:
        data['report'] = 'watchpointReport{}'.format(watch_id)
    else:
        data['report'] = 'plotXYReport'
    return '''
{}

import Shadow.ShadowTools
Shadow.ShadowTools.plotxy(beam, 1, 3, nbins=100, nolost=1)
    '''.format(_generate_parameters_file(data, is_parallel=True))


def remove_last_frame(run_dir):
    pass


def resource_files():
    return pkio.sorted_glob(_RESOURCE_DIR.join('*.txt'))


def validate_delete_file(data, filename, file_type):
    """Returns True if the filename is in use by the simulation data."""
    return filename in _simulation_files(data)


def validate_file(file_type, path):
    pass


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(
            data,
            run_dir,
            is_parallel,
        ),
    )


def _convert_meters_to_centimeters(models):
    for m in models:
        if isinstance(m, dict):
            name = m['type']
            model = m
        else:
            name = m
            model = models[m]
        if name in _CENTIMETER_FIELDS:
            for f in _CENTIMETER_FIELDS[name]:
                model[f] *= 100


def _eq(item, field, *values):
    t = _SCHEMA.model[item['type']][field][1]
    for v, n in _SCHEMA.enum[t]:
        if item[field] == v:
            return n in values
    raise AssertionError(
        '{}: value not found for model={} field={} type={}'.format(
            item[field], item['type'], field, t))


def _field_value(name, field, value):
    return "\n{}.{} = {}".format(name, field.upper(), value)


def _fields(name, item, fields):
    res = ''
    for f in fields:
        field_name = _FIELD_ALIAS.get(f, f)
        res += _field_value(name, field_name, item[f])
    return res


def _generate_autotune_element(item):
    res = _item_field(item, ['f_central'])
    if item['type'] == 'grating' or item.f_central == '0':
        res += _item_field(item, ['t_incidence', 't_reflection'])
    if item.f_central == '1':
        res += _item_field(item, ['f_phot_cent'])
        if item.f_phot_cent == '0':
            res += _item_field(item, ['phot_cent'])
        elif item.f_phot_cent == '1':
            res += _item_field(item, ['r_lambda'])
    return res


def _generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    res = ''
    prev_position = 0
    last_element = False
    count = 0
    for i in range(len(beamline)):
        item = beamline[i]
        if _is_disabled(item):
            continue
        count += 1
        source_distance = item.position - prev_position
        image_distance = 0
        for j in range(i + 1, len(beamline)):
            next_item = beamline[j]
            if _is_disabled(next_item):
                continue
            image_distance = next_item.position - item.position
            break
        theta_recalc_required = item['type'] in ('crystal', 'grating') and item['f_default'] == '1' and item['f_central'] == '1'
        if item['type'] == 'crl':
            count, res = _generate_crl(item, source_distance, count, res)
        else:
            res += '\n\noe = Shadow.OE()' + _field_value('oe', 'dummy', '1.0')
            if item['type'] == 'aperture' or item['type'] == 'obstacle':
                res += _generate_screen(item)
            elif item['type'] == 'mirror':
                res += _generate_element(item, source_distance, image_distance)
                res += _generate_mirror(item)
            elif item['type'] == 'crystal':
                res += _generate_element(item, source_distance, image_distance)
                res += _generate_crystal(item)
            elif item['type'] == 'grating':
                res += _generate_element(item, source_distance, image_distance)
                res += _generate_grating(item)
            elif item['type'] == 'watch':
                res += "\n" + 'oe.set_empty()'
                if last_id and last_id == int(item['id']):
                    last_element = True
            else:
                raise RuntimeError('unknown item type: {}'.format(item))
            if theta_recalc_required:
                res += '''
# use shadow to calculate THETA from the default position
# but do not advance the original beam to the image depth
calc_beam = beam.duplicate()
calc_oe = oe.duplicate()
calc_oe.F_DEFAULT = 1
calc_oe.T_SOURCE = calc_oe.SSOUR
calc_oe.T_IMAGE = calc_oe.SIMAG
calc_beam.traceOE(calc_oe, 1)
oe.THETA = calc_oe.T_INCIDENCE * 180.0 / math.pi
'''
            res += _field_value('oe', 'fwrite', '3') \
                   + _field_value('oe', 't_image', 0.0) \
                   + _field_value('oe', 't_source', source_distance) \
                   + "\n" + 'beam.traceOE(oe, {})'.format(count)
        if last_element:
            break
        prev_position = item.position
    return res


def _generate_bending_magnet(data):
    return _source_field(data['models']['electronBeam'], ['sigmax', 'sigmaz', 'epsi_x', 'epsi_z', 'bener', 'epsi_dx', 'epsi_dz', 'f_pol']) \
          + _source_field(data['models']['sourceDivergence'], ['hdiv1', 'hdiv2', 'vdiv1', 'vdiv2']) \
          + _field_value('source', 'f_phot', 0) \
          + _field_value('source', 'fsource_depth', 4) \
          + _field_value('source', 'f_color', 3) \
          + _source_field(data['models']['bendingMagnet'], ['r_magnet', 'ph1', 'ph2', 'fdistr']) \
          + _field_value('source', 'r_aladdin', 'source.R_MAGNET * 100')


def _generate_crl(item, source_distance, count, res):
    for n in range(item.numberOfLenses):
        res += _generate_crl_lens(
            item,
            n == 0,
            n == (item.numberOfLenses - 1),
            count,
            source_distance,
        )
        count += 2
    return count - 1, res


def _generate_crl_lens(item, is_first, is_last, count, source):

    half_lens = item.lensThickness / 2.0
    source_width = item.pilingThickness / 2.0 - half_lens
    diameter = item.rmirr * 2.0

    def _half(is_obj, **values):
        is_ima = not is_obj
        values = pkcollections.Dict(values)
        # "10" is "conic", but it's only valid if useCCC, which
        # are the external coefficients. The "shape" values are still
        # valid
        which = 'obj' if is_obj else 'ima'
        values.update({
            'r_attenuation_' + which: item.attenuationCoefficient,
            'r_ind_' + which: item.refractionIndex,
        })
        if _eq(item, 'fmirr', 'Spherical', 'Paraboloid'):
            ccc = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, diameter, 0.0]
            if bool(_eq(item, 'initialCurvature', 'Convex')) == is_ima:
                values.f_convex = 1
            else:
                # Inverse diameter for concave surface
                ccc[8] = -ccc[8]
            if _eq(item, 'useCCC', 'Yes'):
                if 'f_convex' in values:
                    del values['f_convex']
            if _eq(item, 'fmirr', 'Paraboloid'):
                ccc[2] = 0.0
            values.ccc = 'numpy.array([{}])'.format(', '.join(map(str, ccc)))
        if is_ima:
            values.update(
                t_image=half_lens,
                t_source=(source if is_first else 0.0) + source_width,
            )
        else:
            values.update(
                t_image=source_width,
                t_source=half_lens,
            )
        fields = sorted(values.keys())
        return '''

oe = Shadow.OE(){}
beam.traceOE(oe, {})'''.format(_fields('oe', values, fields), count + is_obj)

    common = pkcollections.Dict(
        dummy=1.0,
        fwrite=3,
    )
    # Same for all lenses (afaict)
    common.update(
        f_ext=1,
        f_refrac=1,
        t_incidence=0.0,
        t_reflection=180.0,
    )
    common.fmirr = item.fmirr
    if not _eq(item, 'fmirr', 'Plane'):
        if _eq(item, 'useCCC', 'Yes'):
            common.fmirr = 10
        if _eq(item, 'fcyl', 'Yes'):
            common.update(
                fcyl=item.fcyl,
                cil_ang=item.cil_ang,
            )
        if _eq(item, 'fmirr', 'Paraboloid'):
            common.param = item.rmirr
        else:
            common.rmirr = item.rmirr
    common.fhit_c = item.fhit_c
    if _eq(item, 'fhit_c', 'Finite'):
        lens_radius = item.lensDiameter / 2.0
        common.update(
            fshape=2,
            rlen2=lens_radius,
            rwidx2=lens_radius,
        )
    return _half(0, **common) + _half(1, **common)


def _generate_crystal(item):
    res = _field_value('oe', 'f_crystal', '1')
    res += _generate_autotune_element(item)
    res += _item_field(item, ['f_refrac', 'f_mosaic'])
    if item.f_mosaic == '0':
        res += _item_field(item, ['f_bragg_a', 'f_johansson'])
        if item.f_bragg_a == '1':
            res += _item_field(item, ['a_bragg', 'thickness'])
            if item.f_refrac == '1':
                res += _item_field(item, ['order'])
        if item.f_johansson == '1':
            res += _field_value('oe', 'f_ext', '1')
            res += _item_field(item, ['r_johansson'])
    elif item.f_mosaic == '1':
        res += _item_field(item, ['spread_mos', 'thickness', 'mosaic_seed'])
    bragg_filename = 'crystal-bragg-{}.txt'.format(item.id)
    # def bragg(interactive=True, DESCRIPTOR="Si",H_MILLER_INDEX=1,K_MILLER_INDEX=1,L_MILLER_INDEX=1,TEMPERATURE_FACTOR=1.0,E_MIN=5000.0,E_MAX=15000.0,E_STEP=100.0,SHADOW_FILE="bragg.dat"):
    res += "\n" + "bragg(interactive=False, DESCRIPTOR='{}', H_MILLER_INDEX={}, K_MILLER_INDEX={}, L_MILLER_INDEX={}, TEMPERATURE_FACTOR={}, E_MIN={}, E_MAX={}, E_STEP={}, SHADOW_FILE='{}')".format(
        item.braggMaterial,
        item.braggMillerH,
        item.braggMillerK,
        item.braggMillerL,
        item.braggTemperaturFactor,
        item.braggMinEnergy,
        item.braggMaxEnergy,
        item.braggEnergyStep,
        bragg_filename,
    )
    res += _field_value('oe', 'file_refl', "b'{}'".format(bragg_filename))
    return res


def _generate_element(item, source_distance, image_distance):
    if item.f_ext == '0':
        # always override f_default - generated t_image is always 0.0
        if item.f_default == '1':
            item.ssour = source_distance
            item.simag = image_distance
            item.theta = item.t_incidence
            item.f_default = '0'
    res = _item_field(item, ['fmirr', 'alpha', 'fhit_c'])
    if item.fmirr in ('1', '2', '3', '4', '7'):
        res += _item_field(item, ['f_ext'])
        if item.f_ext == '0':
            res += _item_field(item, ['f_default', 'ssour', 'simag', 'theta'])
    if item.fmirr in ('1', '2', '4', '7'):
        res += _item_field(item, ['f_convex', 'fcyl'])
        if item.fcyl == '1':
            res += _item_field(item, ['cil_ang'])
    if item.fmirr == '1':
        if item.f_ext == '1':
            res += _item_field(item, ['rmirr'])
    elif item.fmirr in ('2', '7'):
        if item.f_ext == '1':
            res += _item_field(item, ['axmaj', 'axmin', 'ell_the'])
    elif item.fmirr == '3':
        res += _item_field(item, ['f_torus'])
        if item.f_ext == '1':
            res += _item_field(item, ['r_maj', 'r_min'])
    elif item.fmirr == '4':
        if item.f_ext == '0':
            res += _item_field(item, ['f_side'])
        else:
            res += _item_field(item, ['param'])
    if item.fhit_c == '1':
        res += _item_field(item, ['fshape'])
        if item.fshape == '1':
            res += _item_field(item, ['halfWidthX1', 'halfWidthX2', 'halfLengthY1', 'halfLengthY2'])
        else:
            res += _item_field(item, ['externalOutlineMajorAxis', 'externalOutlineMinorAxis'])
            if item.fshape == '3':
                res += _item_field(item, ['internalOutlineMajorAxis', 'internalOutlineMinorAxis'])
    return res


def _generate_geometric_source(data):
    geo = data['models']['geometricSource']
    res = _source_field(geo, ['fsour', 'wxsou', 'wzsou', 'sigmax', 'sigmaz', 'fdistr', 'sigdix', 'sigdiz', 'cone_max', 'cone_min', 'fsource_depth', 'wysou', 'sigmay', 'f_color', 'f_polar', 'f_coher', 'pol_angle', 'pol_deg']) \
          + _source_field(data['models']['sourceDivergence'], ['hdiv1', 'hdiv2', 'vdiv1', 'vdiv2']) \
          + _field_value('source', 'f_phot', 0)
    if geo['f_color'] == '1':
        res += _source_field(geo, ['singleEnergyValue'])
    else:
        res += _source_field(geo, ['ph1', 'ph2'])
    return res


def _generate_grating(item):
    res = _field_value('oe', 'f_grating', '1')
    res += _generate_autotune_element(item)
    res += _item_field(item, ['f_ruling', 'order'])
    if item.f_ruling in ('0', '1'):
        res += _item_field(item, ['rulingDensity'])
    elif item.f_ruling == '2':
        res += _item_field(item, ['holo_r1', 'holo_r2', 'holo_del', 'holo_gam', 'holo_w', 'holo_rt1', 'holo_rt2', 'f_pw', 'f_pw_c', 'f_virtual'])
    elif item.f_ruling == '3':
        res += _item_field(item, ['rulingDensityCenter'])
    elif item.f_ruling == '5':
        res += _item_field(item, ['rulingDensityPolynomial', 'f_rul_abs', 'rul_a1', 'rul_a2', 'rul_a3', 'rul_a4'])
    if item.f_central == '1':
        res += _item_field(item, ['f_mono'])
        if item.f_mono == '4':
            res += _item_field(item, ['f_hunt', 'hunt_h', 'hunt_l', 'blaze'])
    return res


def _generate_mirror(item):
    item.t_reflection = item.t_incidence
    res = _item_field(item, ['t_incidence', 't_reflection'])

    if item.f_reflec in ('1', '2'):
        res += _item_field(item, ['f_reflec'])
        if item.f_refl == '0':
            prerefl_filename = 'mirror-prerefl-{}.txt'.format(item.id)
            res += "\n" + "prerefl(interactive=False, SYMBOL='{}', DENSITY={}, FILE='{}', E_MIN={}, E_MAX={}, E_STEP={})".format(
                item.prereflElement,
                item.prereflDensity,
                prerefl_filename,
                item.reflectivityMinEnergy,
                item.reflectivityMaxEnergy,
                item.prereflStep,
            )
            res += _field_value('oe', 'file_refl', "b'{}'".format(prerefl_filename))
        elif item.f_refl == '2':
            mlayer_filename = 'mirror-pre_mlayer-{}.txt'.format(item.id)
            res += "\n" + "pre_mlayer(interactive=False, FILE='{}',E_MIN={},E_MAX={},S_DENSITY={},S_MATERIAL='{}',E_DENSITY={},E_MATERIAL='{}',O_DENSITY={},O_MATERIAL='{}',N_PAIRS={},THICKNESS={},GAMMA={},ROUGHNESS_EVEN={},ROUGHNESS_ODD={})".format(
                mlayer_filename,
                item.reflectivityMinEnergy,
                item.reflectivityMaxEnergy,
                item.mlayerSubstrateDensity,
                item.mlayerSubstrateMaterial,
                item.mlayerEvenSublayerDensity,
                item.mlayerEvenSublayerMaterial,
                item.mlayerOddSublayerDensity,
                item.mlayerOddSublayerMaterial,
                item.mlayerBilayerNumber,
                item.mlayerBilayerThickness,
                item.mlayerGammaRatio,
                item.mlayerEvenRoughness,
                item.mlayerOddRoughness,
            )
            res += _field_value('oe', 'file_refl', "b'{}'".format(mlayer_filename))
            res += _item_field(item, ['f_refl', 'f_thick'])
    return res


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    _validate_data(data, simulation_db.get_schema(SIM_TYPE))
    _convert_meters_to_centimeters(data['models'])
    _convert_meters_to_centimeters(data['models']['beamline'])
    v = template_common.flatten_data(data['models'], {})
    r = data['report']
    report_model = data['models'][r]
    beamline = data['models']['beamline']
    v['shadowOutputFile'] = _SHADOW_OUTPUT_FILE

    if r == 'initialIntensityReport':
        v['distanceFromSource'] = beamline[0]['position'] if len(beamline) else template_common.DEFAULT_INTENSITY_DISTANCE
    elif template_common.is_watchpoint(r):
        v['beamlineOptics'] = _generate_beamline_optics(data['models'], template_common.watchpoint_id(r))
    else:
        v['distanceFromSource'] = report_model['distanceFromSource']

    if v['simulation_sourceType'] == 'bendingMagnet':
        v['bendingMagnetSettings'] = _generate_bending_magnet(data)
    elif v['simulation_sourceType'] == 'geometricSource':
        v['geometricSourceSettings'] = _generate_geometric_source(data)
    elif v['simulation_sourceType'] == 'wiggler':
        v['wigglerSettings'] = _generate_wiggler(data)
        v['wigglerTrajectoryFilename'] = _WIGGLER_TRAJECTOR_FILENAME
        v['wigglerTrajectoryInput'] = ''
        if data['models']['wiggler']['b_from'] in ('1', '2'):
            v['wigglerTrajectoryInput'] = _wiggler_file(data['models']['wiggler']['trajFile'])
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_screen(item):
    return "\n" + 'oe.set_empty().set_screens()' \
        + _field_value('oe', 'i_slit[0]', '1') \
        + _field_value('oe', 'k_slit[0]', 0 if item['type'] == 'aperture' else 1) \
        + _item_field(item, ['horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'])


def _generate_wiggler(data):
    return _source_field(data['models']['electronBeam'], ['sigmax', 'sigmaz', 'epsi_x', 'epsi_z', 'bener', 'epsi_dx', 'epsi_dz']) \
          + _source_field(data['models']['wiggler'], ['ph1', 'ph2']) \
          + _field_value('source', 'fdistr', 0) \
          + _field_value('source', 'fsource_depth', 0) \
          + _field_value('source', 'f_wiggler', 1) \
          + _field_value('source', 'conv_fact', 100.0) \
          + _field_value('source', 'hdiv1', 1.0) \
          + _field_value('source', 'hdiv2', 1.0) \
          + _field_value('source', 'vdiv1', 1.0) \
          + _field_value('source', 'vdiv2', 1.0) \
          + _field_value('source', 'f_color', 0) \
          + _field_value('source', 'f_phot', 0) \
          + _field_value('source', 'file_traj', "b'{}'".format(_WIGGLER_TRAJECTOR_FILENAME))


def _item_field(item, fields):
    return _fields('oe', item, fields)


def _is_disabled(item):
    return 'isDisabled' in item and item['isDisabled']


def _simulation_files(data):
    res = []
    if data['models']['simulation']['sourceType'] == 'wiggler':
        if data['models']['wiggler']['b_from'] in ('1', '2'):
            res.append(_wiggler_file(data['models']['wiggler']['trajFile']))
    return res


def _source_field(model, fields):
    return _fields('source', model, fields)


def _validate_data(data, schema):
    template_common.validate_models(data, schema)


def _wiggler_file(value):
    return template_common.lib_file_name('wiggler', 'trajFile', value)
