# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import copy
import sirepo.sim_data
import re
import sirepo.util


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

OUTPUT_NAME = 'abc.dat'


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    f = run_dir.join(OUTPUT_NAME)
    return f.basename, f.read(), 'text/csv'


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    # validate something
    #m = re.search('^user_alert=(.*)', data.models.<???>)
    #if m:
    #    raise sirepo.util.UserAlert(m.group(1), 'log msg should not be sent')
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    if 'report' in data:
        # validate report name(s) ?
        # assert data['report'] == 'heightWeightReport', \
        #    'unknown report: {}'.format(data['report'])
        pass
    v = copy.deepcopy(data['models'], pkcollections.Dict())
    # add parameters
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
