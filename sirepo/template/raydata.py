# -*- coding: utf-8 -*-
u"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo.template import template_common
import base64
import databroker
import glob
import os
import re
import sirepo.sim_data
import sirepo.util


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

# TODO(e-carlin): from user
_BROKER_NAME = 'chx'

# TODO(e-carlin): from user
_SCAN_UID = 'bdcce1f3-7317-4775-bc26-ece8f0612758'

# POSIT: Matches data_dir in
# https://github.com/radiasoft/raydata/blob/main/AnalysisNotebooks/XPCS_SAXS/XPCS_SAXS.ipynb
_RESULTS_DIR = '2021_1/vagrant/Results/' + _SCAN_UID.split('-')[0] + '/'

_OUTPUT_FILE = 'out.ipynb'



# The metadata fields are from bluesky. Some have spaces while others don't.
_METDATA = PKDict(
    analysis=(
        'analysis',
        'auto_pipeline',
        'detectors',
        'number of images',
    ),
    general= (
        'beamline_id',
        'cycle',
        'data path',
        'owner',
        'time',
        'uid',
    ),
    plan= (
        'plan_args',
        'plan_name',
        'plan_type',
        'scan_id',
        'sequence id',
    ),
)


def background_percent_complete(report, run_dir, is_running):
    def _png_filenames():
        return [
            pkio.py_path(f).basename for f in sorted(
                glob.glob(str(run_dir.join(_RESULTS_DIR, '*.png'))),
                key=os.path.getmtime
            )
        ]

    def _sanitized_name(filename):
        return sirepo.util.INVALID_PYTHON_IDENTIFIER.sub('_', filename) + 'Animation'

    res = PKDict(
        pngOutputFiles=[
            PKDict(name=_sanitized_name(f), filename=f) for f in _png_filenames()
        ],
    )
    res.pkupdate(frameCount=len(res.pngOutputFiles))
    if is_running:
        return res.pkupdate(percentComplete=0)
    return res.pkupdate(percentComplete=100)


def sim_frame(frame_args):
    return PKDict(image=pkcompat.from_bytes(
        base64.b64encode(
            pkio.read_binary(
                sirepo.util.safe_path(frame_args.run_dir, _RESULTS_DIR, frame_args.filename),
            ),
        ),
    ))


def stateless_compute_metadata(data):
    return PKDict(data=_metadata(data))


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(
            input_name=data.models.analysisAnimation.notebook,
            output_name=_OUTPUT_FILE,
        ),
    )


def _metadata(data):
    res = PKDict()
    for k in _METDATA[data.category]:
        res[
            ' '.join(k.split('_'))
        ] = databroker.catalog[_BROKER_NAME][_SCAN_UID].metadata['start'][k]
    return res
