# -*- coding: utf-8 -*-
"""Wrapper to run shadow from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
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
    """Run shadow in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run shadow in
    """
    beam = template_common.exec_parameters().beam
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
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
        ticket = beam.histo2(int(model['x']), int(model['y']), nbins=template_common.histogram_bins(model['histogramBins']), ref=int(model['weight']), nolost=1, calculate_widths=0, xrange=x_range, yrange=y_range)
        _scale_ticket(ticket)
        values = ticket['histogram'].T
        if numpy.isnan(values).any():
            # something failed, look for errors in log
            simulation_db.write_result({
                'error': _parse_shadow_error(cfg_dir)
            })
            return
        res = {
            'x_range': [ticket['xrange'][0], ticket['xrange'][1], ticket['nbins_h']],
            'y_range': [ticket['yrange'][0], ticket['yrange'][1], ticket['nbins_v']],
            'x_label': _label_with_units(model['x'], column_values),
            'y_label': _label_with_units(model['y'], column_values),
            'z_label': 'Frequency',
            'title': u'{}, {}'.format(_label(model['x'], column_values), _label(model['y'], column_values)),
            'z_matrix': values.tolist(),
            'frameCount': 1,
        }
    else:
        weight = int(model['weight'])
        ticket = beam.histo1(int(model['column']), nbins=template_common.histogram_bins(model['histogramBins']), ref=weight, nolost=1, calculate_widths=0)
        _scale_ticket(ticket)
        res = {
            'title': _label(model['column'], column_values),
            'x_range': [ticket['xrange'][0], ticket['xrange'][1], ticket['nbins']],
            'y_label': u'{}{}'.format(
                'Number of Rays',
                u' weighted by {}'.format(_label_for_weight(model['weight'], column_values)) if weight else ''),
            'x_label': _label_with_units(model['column'], column_values),
            'points': ticket['histogram'].T.tolist(),
            'frameCount': 1,
        }
        #pkdlog('range amount: {}', res['x_range'][1] - res['x_range'][0])
        #1.55431223448e-15
        dist = res['x_range'][1] - res['x_range'][0]
        #TODO(pjm): only rebalance range if outside of 0
        if dist < 1e-14:
            #TODO(pjm): include offset range for client
            res['x_range'][0] = 0
            res['x_range'][1] = dist
    simulation_db.write_result(res)


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


def _parse_shadow_error(run_dir):
    run_dir = py.path.local(run_dir)
    if run_dir.join(template_common.RUN_LOG).exists():
        text = pkio.read_text(run_dir.join(template_common.RUN_LOG))
        for line in text.split("\n"):
            if re.search(r'invalid chemical formula', line):
                return 'A mirror contains an invalid reflectivity material'
    return 'an unknown error occurred'


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


def _script():
    return pkio.read_text()
