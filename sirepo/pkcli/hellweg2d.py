# -*- coding: utf-8 -*-
"""Wrapper to run Hellweg2D from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from rslinac.solver import BeamSolver
from sirepo import simulation_db
from sirepo.template import template_common, hellweg2d_dump_reader
import numpy
import sirepo.template.hellweg2d as template

_HELLWEG2D_DUMP_FILE = 'all-data.bin'
_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)

def run(cfg_dir):
    """Run Hellweg2D in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run hellweg2d in
    """
    with pkio.save_chdir(cfg_dir):
        _run_hellweg2d()
        beam_info = hellweg2d_dump_reader.beam_info(_HELLWEG2D_DUMP_FILE, 0)
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        report = data['models'][data['report']]
        res = None
        if data['report'] == 'beamReport':
            x, y = report.reportType.split('-')
            data_list = [
                hellweg2d_dump_reader.get_points(beam_info, x),
                hellweg2d_dump_reader.get_points(beam_info, y),
            ]
            hist, edges = numpy.histogramdd(data_list, template_common.histogram_bins(report.histogramBins))
            res = {
                'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
                'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
                'x_label': hellweg2d_dump_reader.get_label(x),
                'y_label': hellweg2d_dump_reader.get_label(y),
                'title': _report_title(report.reportType, _SCHEMA['enum']['BeamReportType']),
                'z_matrix': hist.T.tolist(),
            }
        elif data['report'] == 'beamHistogramReport':
            points = hellweg2d_dump_reader.get_points(beam_info, report.reportType)
            hist, edges = numpy.histogram(points, template_common.histogram_bins(report.histogramBins))
            res = {
                'title': _report_title(report.reportType, _SCHEMA['enum']['BeamHistogramReportType']),
                'x_range': [edges[0], edges[-1]],
                'y_label': 'Number of Particles',
                'x_label': hellweg2d_dump_reader.get_label(report.reportType),
                'points': hist.T.tolist(),
                'frameCount': 1,
            }
        else:
            raise RuntimeError('unknown report: {}'.format(data['report']))
        simulation_db.write_result(res)


def run_background(cfg_dir):
    pass


def _report_title(report_type, enum_values):
    for e in enum_values:
        if e[0] == report_type:
            return e[1]
    raise RuntimeError('unknown report type: {}'.format(report_type))


def _run_hellweg2d(bunch_report=False, with_mpi=False):
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    pkio.write_text('input.txt', input_file)
    pkio.write_text('defaults.ini', '')
    solver = BeamSolver('defaults.ini', 'input.txt')
    solver.solve()
    solver.save_output('output.txt')
    solver.dump_bin(_HELLWEG2D_DUMP_FILE)
