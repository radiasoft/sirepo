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

_HELLWEG2D_DUMP_FILE = 'all-data.bin'


def run(cfg_dir):
    """Run Hellweg2D in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run hellweg2d in
    """
    with pkio.save_chdir(cfg_dir):
        _run_hellweg2d()
        beam_info = hellweg2d_dump_reader.beam_info(_HELLWEG2D_DUMP_FILE, 0)
        data_list = [
            hellweg2d_dump_reader.get_points(beam_info, 'x'),
            hellweg2d_dump_reader.get_points(beam_info, 'y'),
        ]
        hist, edges = numpy.histogramdd(data_list, template_common.histogram_bins('100'))
        res = {
            'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
            'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
            'x_label': 'X [m]',
            'y_label': 'Y [m]',
            'title': 'X-Y Plot',
            'z_matrix': hist.T.tolist(),
        }
        simulation_db.write_result(res)


def run_background(cfg_dir):
    pass


def _run_hellweg2d(bunch_report=False, with_mpi=False):
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    pkio.write_text('input.txt', input_file)
    pkio.write_text('defaults.ini', '')
    solver = BeamSolver('defaults.ini', 'input.txt')
    solver.solve()
    solver.save_output('output.txt')
    solver.dump_bin(_HELLWEG2D_DUMP_FILE)
