# -*- coding: utf-8 -*-
"""Wrapper to run RS4PI from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from dicompylercore import dicomparser, dvhcalc
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc
from sirepo import feature_config
from sirepo import simulation_db
from sirepo.template import template_common
import numpy as np
import py.path
import sirepo.template.rs4pi as template
import struct
import time


def run(cfg_dir):
    cfg_dir = pkio.py_path(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data['report'] == 'doseCalculation':
        _run_dose_calculation(data, cfg_dir)
    elif data['report'] == 'dvhReport':
        _run_dvh(data, cfg_dir)
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        simulation_db.write_result({})


def _parent_file(cfg_dir, filename):
    return str(pkio.py_path(cfg_dir.dirname).join(filename))


def _run_dose_calculation(data, cfg_dir):
    if not feature_config.cfg.rs4pi_dose_calc:
        return _run_dose_calculation_fake(data, cfg_dir)
    with pkio.save_chdir(cfg_dir):
        pksubprocess.check_call_with_signals(['bash', str(cfg_dir.join(template.DOSE_CALC_SH))])
        dicom_dose = template.generate_rtdose_file(data, cfg_dir)
        data['models']['dicomDose'] = dicom_dose
        # save results into simulation input data file, this is needed for further calls to get_simulation_frame()
        simulation_db.write_json(template_common.INPUT_BASE_NAME, data)
        simulation_db.write_result({
            'dicomDose': dicom_dose,
        })


def _run_dose_calculation_fake(data, cfg_dir):
    time.sleep(5)
    simulation_db.write_result({})


def _run_dvh(data, cfg_dir):
    if not len(data['models']['dvhReport']['roiNumbers']):
        simulation_db.write_result({
            'error': 'No selection',
        })
    y_range = None
    plots = []
    for roi_number in data['models']['dvhReport']['roiNumbers']:
        roi_number = int(roi_number)
        dp = dicomparser.DicomParser(_parent_file(cfg_dir, template.RTSTRUCT_EXPORT_FILENAME))
        for roi in dp.ds.ROIContourSequence:
            if roi.ReferencedROINumber == roi_number:
                for c in roi.ContourSequence:
                    if 'ContourImageSequence' not in c:
                        c.ContourImageSequence = []
        s = dp.GetStructures()[roi_number]
        s['planes'] = dp.GetStructureCoordinates(roi_number)
        s['thickness'] = dp.CalculatePlaneThickness(s['planes'])

        rtdose = dicomparser.DicomParser(_parent_file(cfg_dir, template._DOSE_DICOM_FILE))
        calcdvh = dvhcalc.calculate_dvh(s, rtdose, None, True, None)
        counts = calcdvh.histogram
        # cumulative
        counts = counts[::-1].cumsum()[::-1]
        # relative volume
        if len(counts) and counts.max() > 0:
            counts = 100 * counts / counts.max()
        bins = np.arange(0, calcdvh.histogram.size + 1.0) / 100.0
        min_y = np.min(counts)
        max_y = np.max(counts)
        if y_range:
            if min_y < y_range[0]:
                y_range[0] = min_y
            if max_y > y_range[1]:
                y_range[1] = max_y
        else:
            y_range = [min_y, max_y]
        plots.append({
            'points': counts.tolist(),
            'color': '#{}'.format(struct.pack('BBB', *s['color']).encode('hex')),
            'label': s['name'],
        })
    res = {
        'title': '',
        'x_range': [bins[0], bins[-1], 100],
        'y_label': 'Volume [%]',
        'x_label': 'Dose [gy]',
        'y_range': y_range,
        'plots': sorted(plots, key=lambda v: v['label'].lower()),
    }
    simulation_db.write_result(res)
