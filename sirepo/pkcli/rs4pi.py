# -*- coding: utf-8 -*-
"""Wrapper to run RS4PI from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from dicompylercore import dicomparser, dvhcalc
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo import feature_config
from sirepo import simulation_db
from sirepo.template import template_common
import numpy as np
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
        raise AssertionError('unknown report: {}'.format(data['report']))


def run_background(cfg_dir):
    pass


def _parent_file(cfg_dir, filename):
    return str(pkio.py_path(cfg_dir.dirname).join(filename))


def _run_dose_calculation(data, cfg_dir):
    dicom_dose = _run_dose_calculation_fake(data, cfg_dir)
    data['models']['dicomDose'] = dicom_dose
    # save results into simulation input data file, this is needed for further calls to get_simulation_frame()
    simulation_db.write_json(template_common.INPUT_BASE_NAME, data)
    template_common.write_sequential_result(PKDict(dicomDose=dicom_dose))


def _run_dose_calculation_fake(data, cfg_dir):
    dicom_dose = data['models']['dicomDose']
    dicom_dose['startTime'] = int(time.time())
    time.sleep(5)
    return dicom_dose


def _run_dvh(data, cfg_dir):
    dvh_report = data['models']['dvhReport']
    assert dvh_report['roiNumbers'], 'No selection'
    y_range = None
    plots = []
    max_x = 0
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
        counts = np.append(calcdvh.histogram, 0.0)
        if dvh_report['dvhType'] == 'cumulative':
            counts = counts[::-1].cumsum()[::-1]
        else:
            counts = np.append(abs(np.diff(counts) * -1), [0])
        if dvh_report['dvhVolume'] == 'relative':
            if dvh_report['dvhType'] == 'differential':
                counts = counts[::-1].cumsum()[::-1]
            if counts.any() and counts.max() > 0:
                counts = 100 * counts / counts.max()
            if dvh_report['dvhType'] == 'differential':
                counts = np.append(abs(np.diff(counts) * -1), [0])
        else:
            counts /= 10
        max_x = max(max_x, counts.size)
        min_y = np.min(counts)
        max_y = np.max(counts)
        if y_range:
            if min_y < y_range[0]:
                y_range[0] = min_y
            if max_y > y_range[1]:
                y_range[1] = max_y
        else:
            y_range = [min_y, max_y]
        rgb = s['color']
        plots.append({
            'points': counts.tolist(),
            'color': '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2])),
            'label': s['name'],
        })
    res = {
        'title': '',
        'x_range': [0, max_x / 100.0, max_x],
        'y_label': 'Volume [{}]'.format('%' if dvh_report['dvhVolume'] == 'relative' else 'm³'),
        'x_label': 'Dose [gy]',
        'y_range': y_range,
        'plots': sorted(plots, key=lambda v: v['label'].lower()),
    }
    template_common.write_sequential_result(res)
