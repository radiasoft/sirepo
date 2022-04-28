# -*- coding: utf-8 -*-
u"""CloudMC execution template.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.sim_data


VOLUME_INFO_FILE = 'volumes.json'
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_DAGMC_FILE = 'dagmc.h5m'


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    if not run_dir.join(VOLUME_INFO_FILE).exists():
        raise AssertionError('Volume extraction failed')
    return PKDict(
        percentComplete=100,
        frameCount=1,
        volumes=simulation_db.read_json(VOLUME_INFO_FILE),
    )


def get_data_file(run_dir, model, frame, **kwargs):
    if model == 'dagmcAnimation':
        return PKDict(filename=run_dir.join(f'{frame}.zip'))
    raise AssertionError(f'No data file for model: {model}')


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    report = data.get('report', '')
    res, v = template_common.generate_parameters_file(data)
    if report == 'dagmcAnimation':
        return ''
    raise AssertionError('Report not yet supported: {}'.format(report))
