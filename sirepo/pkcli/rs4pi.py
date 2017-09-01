# -*- coding: utf-8 -*-
"""Wrapper to run RS4PI from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.rs4pi as template
import py.path


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data['report'] == 'doseCalculation':
        _run_dose_calculation(data, py.path.local(cfg_dir))
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        simulation_db.write_result({})


def _run_dose_calculation(data, cfg_dir):
    filename = template.generate_rtstruct_file(cfg_dir.join('..'), cfg_dir)
    roiNumber = data['models']['dicomEditorState']['selectedPTV']
    #TODO(pjm): rtstruct dicom file is available at template.RTSTRUCT_EXPORT_FILENAME
    # run dose calculation for the selected roiNumber
    simulation_db.write_result({})
