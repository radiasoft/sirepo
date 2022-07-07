# -*- coding: utf-8 -*-
"""Wrapper to run RCSCON from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import sdds_util
from sirepo.template import template_common
import numpy as np
import py.path
import sirepo.template.rcscon as template


def run(cfg_dir):
    template_common.exec_parameters()
    template.extract_report_data(
        py.path.local(cfg_dir),
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
    )


def run_background(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == 'elegantAnimation':
        return _run_elegant_simulation(cfg_dir)
    template_common.exec_parameters()


def _build_arrays():
    sigma = sdds_util.read_sdds_pages(
        'run_setup.sigma.sdds',
        ['s', 's1', 's12', 's2', 's3', 's34', 's4', 's5', 's56', 's6'],
    )
    errors = _error_values()
    inputs = []
    outputs = []
    k = 0
    for i in range(len(errors)):
        for j in range(int(len(sigma.s) / len(errors))):
            initial_index = k - j
            inputs.append([
                errors[i, 1], errors[i, 2], sigma.s[k],
                sigma.s1[initial_index], sigma.s12[initial_index], sigma.s2[initial_index],
                sigma.s3[initial_index], sigma.s34[initial_index], sigma.s4[initial_index],
                sigma.s5[initial_index], sigma.s56[initial_index], sigma.s6[initial_index],
            ])
            outputs.append([
                sigma.s1[k], sigma.s12[k], sigma.s2[k],
                sigma.s3[k], sigma.s34[k], sigma.s4[k],
                sigma.s5[k], sigma.s56[k], sigma.s6[k],
            ])
            k+=1
    return np.asarray(inputs), np.asarray(outputs)


def _error_values():
    pages = sdds_util.read_sdds_pages(
        'error_control.error_log.sdds',
        ['ElementParameter', 'ParameterValue'],
        True)
    res = []
    for page in range(len(pages.ElementParameter)):
        values = PKDict()
        for idx in range(len(pages.ElementParameter[page])):
            p = pages.ElementParameter[page][idx]
            v = pages.ParameterValue[page][idx]
            if p not in values:
                values[p] = []
            values[p].append(v)
        res.append(
            [page, np.mean(np.asarray(values.PHASE)), np.sum(np.asarray(values.VOLT))],
        )
    return np.asarray(res)


def _run_elegant_simulation(cfg_dir):
    import sirepo.pkcli.elegant
    sirepo.pkcli.elegant.run_elegant()
    inputs, outputs = _build_arrays()
    common = [
        's1', 's12', 's2',
        's3', 's34', 's4',
        's5', 's56', 's6',
    ]
    in_cols = ['average phase', 'total volts', 'position']
    in_header = ','.join(in_cols + ['initial ' + x for x in common])
    out_header = ','.join(common)
    np.savetxt('inputs.csv', inputs, delimiter=',', comments='', header=in_header)
    np.savetxt('outputs.csv', outputs, delimiter=',', comments='', header=out_header)
