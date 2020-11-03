# -*- coding: utf-8 -*-
u"""Controls execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import sirepo.template.madx


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        monitorValues=sirepo.template.madx.extract_monitor_values(run_dir),
    )


def python_source_for_model(data, model):
    return sirepo.template.madx.python_source_for_model(data.models.externalLattice, model)


def write_parameters(data, run_dir, is_parallel):
    data.models.externalLattice.report = ''
    sirepo.template.madx.write_parameters(data.models.externalLattice, run_dir, is_parallel)
