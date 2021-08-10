# -*- coding: utf-8 -*-
"""Wrapper to run shadow from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from sirepo import simulation_db
from sirepo.template import template_common
import numpy
import py.path
import re
import sirepo.template.shadow as template


_MM_TO_CM = 0.1
_CM_TO_M = 0.01
_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)

_SCALE_COLUMNS = [1, 2, 3, 13, 20]
_PLOT_LABELS = {
    '1': ['X [m]'],
    '2': ['Y [m]'],
    '3': ['Z [m]'],
    '4': ["X' [rad]"],
    '5': ["Y' [rad]"],
    '6': ["Z' [rad]"],
    '11': ['Energy [eV]', 'E [eV]'],
    '13': ['Optical Path [m]', 's'],
    '14': [u'Phase s [rad]', u'ϕ s [rad]'],
    '15': [u'Phase p [rad]', u'ϕ p [rad]'],
    '19': [u'Wavelength [Å]', u'λ [Å]'],
    '20': [u'R = sqrt(X² + Y² + Z²) [m]', 'R [m]'],
    '21': [u'Theta (angle from Y axis) [rad]', u'θ [rad]'],
    '22': ['Magnitude = |Es| + |Ep|', '|Es| + |Ep|'],
    '23': [u'Total Intensity = |Es|² + |Ep|²', u'|Es|² + |Ep|²'],
    '24': [u'S Intensity = |Es|²', u'|Es|²'],
    '25': [u'P Intensity = |Ep|²', u'|Ep|²'],
    '26': [u'|K| [Å⁻¹]'],
    '27': [u'K X [Å⁻¹]'],
    '28': [u'K Y [Å⁻¹]'],
    '29': [u'K Z [Å⁻¹]'],
    '30': [u'S0-stokes = |Ep|² + |Es|²', 'S0'],
    '31': [u'S1-stokes = |Ep|² - |Es|²', 'S1'],
    '32': ['S2-stokes = 2|Es||Ep|cos(Phase s-Phase p)', 'S2'],
    '33': ['S3-stokes = 2|Es||Ep|sin(Phase s-Phase p)', 'S3'],
}

def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == 'beamStatisticsReport':
        res = _run_beam_statistics(cfg_dir, data)
    else:
        res = _run_shadow(cfg_dir, data)
    template_common.write_sequential_result(res)


def run_background(cfg_dir):
    pass


def _label(column, values):
    for v in values:
        if column == v[0]:
            return v[1]
    raise RuntimeError('unknown column value: ', column)


def _label_for_weight(column, values):
    if column in _PLOT_LABELS:
        if len(_PLOT_LABELS[column]) > 1:
            return _PLOT_LABELS[column][1]
        return _PLOT_LABELS[column][0]
    return _label(column, values)


def _label_with_units(column, values):
    if column in _PLOT_LABELS:
        return _PLOT_LABELS[column][0]
    return _label(column, values)


def _beam_statistics_values(beam_stats, field):
    if field == 'sigmaxz':
        return [-record.sigma_mx[0][2] if record.isRotated else record.sigma_mx[0][2] for record in beam_stats]
    if field == 'sigmaxpzp':
        return [-record.sigma_mx[1][3] if record.isRotated else record.sigma_mx[1][3] for record in beam_stats]
    if re.search('z', field):
        rotated_field = re.sub('z', 'x', field)
    else:
        rotated_field = re.sub('x', 'z', field)
    return [record[rotated_field] if record.isRotated else record[field] for record in beam_stats]


def _run_beam_statistics(cfg_dir, data):
    template_common.exec_parameters()
    report = data.models.beamStatisticsReport
    d = pkjson.load_any(py.path.local(cfg_dir).join(template.BEAM_STATS_FILE))
    x = [record.s for record in d]
    plots = []

    for y in ('y1', 'y2', 'y3'):
        if report[y] == 'none':
            continue
        label = report[y]
        if label in ('sigmax', 'sigmaz'):
            label += ' [m]'
        elif label in ('sigdix', 'sigdiz', 'angxz', 'angxpzp'):
            label += ' [rad]'
        plots.append(PKDict(
            field=report[y],
            label=label,
        ))
    for item in d:
        for p in plots:
            if p.field == 'angxz':
                sigmax = numpy.array(_beam_statistics_values(d, 'sigmax'))
                sigmaz = numpy.array(_beam_statistics_values(d, 'sigmaz'))
                sigmaxz = numpy.array(_beam_statistics_values(d, 'sigmaxz'))
                p.points = ((1/2) * numpy.arctan(2.e-4 * sigmaxz / (sigmax ** 2 - sigmaz ** 2))).tolist()
            elif p.field == 'angxpzp':
                sigdix = numpy.array(_beam_statistics_values(d, 'sigdix'))
                sigdiz = numpy.array(_beam_statistics_values(d, 'sigdiz'))
                sigmaxpzp = numpy.array(_beam_statistics_values(d, 'sigmaxpzp'))
                p.points = ((1/2) * numpy.arctan(2 * sigmaxpzp / (sigdix ** 2 - sigdiz ** 2))).tolist()
            else:
                p.points = _beam_statistics_values(d, p.field)
    return PKDict(
        aspectRatio=0.3,
        title='',
        x_range=[min(x), max(x)],
        y_label='',
        x_label='s [m]',
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def _run_shadow(cfg_dir, data):
    beam = template_common.exec_parameters().beam
    model = data['models'][data['report']]
    column_values = _SCHEMA['enum']['ColumnValue']

    if 'y' in model:
        x_range = None
        y_range = None
        if model['overrideSize'] == '1':
            x_range = (numpy.array([
                model['horizontalOffset'] - model['horizontalSize'] / 2,
                model['horizontalOffset'] + model['horizontalSize'] / 2,
            ]) * _MM_TO_CM).tolist()
            y_range = (numpy.array([
                model['verticalOffset'] - model['verticalSize'] / 2,
                model['verticalOffset'] + model['verticalSize'] / 2,
            ]) * _MM_TO_CM).tolist()
        ticket = beam.histo2(
            int(model['x']),
            int(model['y']),
            nbins=template_common.histogram_bins(model['histogramBins']),
            ref=int(model['weight']),
            nolost=1,
            calculate_widths=0,
            xrange=x_range,
            yrange=y_range,
        )
        _scale_ticket(ticket)
        values = ticket['histogram'].T
        assert not numpy.isnan(values).any(), 'nan values found'
        res = PKDict(
            x_range=[ticket['xrange'][0], ticket['xrange'][1], ticket['nbins_h']],
            y_range=[ticket['yrange'][0], ticket['yrange'][1], ticket['nbins_v']],
            x_label=_label_with_units(model['x'], column_values),
            y_label=_label_with_units(model['y'], column_values),
            z_label='Intensity' if int(model['weight']) else 'Rays',
            title=u'{}, {}'.format(_label(model['x'], column_values), _label(model['y'], column_values)),
            z_matrix=values.tolist(),
            frameCount=1,
        )
    else:
        weight = int(model['weight'])
        ticket = beam.histo1(
            int(model['column']),
            nbins=template_common.histogram_bins(model['histogramBins']),
            ref=weight,
            nolost=1,
            calculate_widths=0,
        )
        _scale_ticket(ticket)
        res = PKDict(
            title=_label(model['column'], column_values),
            x_range=[ticket['xrange'][0], ticket['xrange'][1], ticket['nbins']],
            y_label=u'{}{}'.format(
                'Number of Rays',
                u' weighted by {}'.format(_label_for_weight(model['weight'], column_values)) if weight else ''),
            x_label=_label_with_units(model['column'], column_values),
            points=ticket['histogram'].T.tolist(),
            frameCount=1,
        )
        #pkdlog('range amount: {}', res['x_range'][1] - res['x_range'][0])
        #1.55431223448e-15
        dist = res['x_range'][1] - res['x_range'][0]
        #TODO(pjm): only rebalance range if outside of 0
        if dist < 1e-14:
            #TODO(pjm): include offset range for client
            res['x_range'][0] = 0
            res['x_range'][1] = dist
    return res


def _scale_ticket(ticket):
    if 'xrange' in ticket:
        col_h = ticket['col_h'] if 'col_h' in ticket else ticket['col']
        if col_h in _SCALE_COLUMNS:
            ticket['xrange'][0] *= _CM_TO_M
            ticket['xrange'][1] *= _CM_TO_M
    if 'yrange' in ticket:
        if ticket['col_v'] in _SCALE_COLUMNS:
            ticket['yrange'][0] *= _CM_TO_M
            ticket['yrange'][1] *= _CM_TO_M
