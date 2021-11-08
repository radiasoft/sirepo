# -*- coding: utf-8 -*-
u"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import base64
import databroker
import databroker.queries
import glob
import os
import sirepo.sim_data
import sirepo.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

# TODO(e-carlin): from user
_CATALOG_NAME = 'chxmulti'

# POSIT: Matches mask_path in
# https://github.com/radiasoft/raydata/blob/main/AnalysisNotebooks/XPCS_SAXS/XPCS_SAXS.ipynb
_MASK_PATH = 'masks'

# TODO(e-carlin): tune this number
_MAX_NUM_SCANS = 1000

_NON_DISPLAY_SCAN_FIELDS = ('uid')

# TODO(e-carlin): from user
_RUN_UID = 'bdcce1f3-7317-4775-bc26-ece8f0612758'

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
                glob.glob(str(run_dir.join('*.png'))),
                key=os.path.getmtime
            )
        ]

    def _sanitized_name(filename):
        return sirepo.util.sanitize_string(filename) + 'Animation'

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
                sirepo.util.safe_path(frame_args.run_dir, frame_args.filename),
            ),
        ),
    ))


def stateless_compute_metadata(data):
    return PKDict(data=_metadata(data))


def stateless_compute_scan_info(data):
    return _scan_info_result(list(map(_scan_info, data.scans)))


def stateless_compute_scans(data):
    s = []
    for i, v in enumerate(_catalog().search(databroker.queries.TimeRange(
            since=data.searchStartTime,
            until=data.searchStopTime,
            timezone='utc',
    )).items()):
        if i > _MAX_NUM_SCANS:
            raise sirepo.util.UserAlert(
                f'More than {_MAX_NUM_SCANS} scans found. Please reduce your query.',
            )
        s.append(_scan_info(v[0], metadata=v[1].metadata))
    return _scan_info_result(s)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )
    m = data.models.inputFiles.mask
    if m:
        d = run_dir.join(_MASK_PATH)
        pkio.mkdir_parent(d)
        for f, b in sirepo.util.read_zip(pkio.py_path(_SIM_DATA.lib_file_name_with_model_field(
                'inputFiles',
                'mask',
                m,
        ))):
            d.join(f).write_binary(b)


def _catalog():
    return databroker.catalog[_CATALOG_NAME]


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
        ] = _catalog()[data.uid].metadata['start'][k]
    return res


def _scan_info(uid, metadata=None):
    m = metadata
    if not m:
        m =  _catalog()[uid].metadata
    return PKDict(
        uid=uid,
        suid=_suid(uid),
        owner=m['start']['owner'],
        start=m['start']['time'],
        stop=m['stop']['time'],
        T_sample_=m['start'].get('T_sample_'),
        sequence_id=m['start']['sequence id'],
    )


def _scan_info_result(scans):
    return PKDict(data=PKDict(
        scans=sorted(scans, key=lambda e: e.start),
        cols=[k for k in scans[0].keys() if k not in _NON_DISPLAY_SCAN_FIELDS] if scans else [],
    ))


def _suid(uid):
    return uid.split('-')[0]
