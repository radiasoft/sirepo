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
import sirepo.feature_config
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.srdb
import sirepo.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

# TODO(e-carlin): from user
_CATALOG_NAME = 'chx'

# TODO(e-carlin): tune this number
_MAX_NUM_SCANS = 1000

_NON_DISPLAY_SCAN_FIELDS = ('uid')

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

_BLUESKY_POLL_TIME_FILE = 'bluesky-poll-time.txt'

def analysis_job_output_files(data):
    def _filename_and_image(path):
        return PKDict(
            filename=path.basename,
            image=pkcompat.from_bytes(
                base64.b64encode(
                    pkio.read_binary(path),
                ),
            )
        )

    def _paths():
        d = _dir_for_scan_uuid(_parse_scan_uuid(data))
        for f in pkio.sorted_glob(d.join('*.png'), key='mtime'):
            yield pkio.py_path(f)

    return PKDict(data=[_filename_and_image(p) for p in _paths()])


def background_percent_complete(report, run_dir, is_running):
    r = PKDict(percentComplete=0 if is_running else 100)
    if report != 'pollBlueskyForScansAnimation':
        return r
    try:
        t = float(pkio.read_text(_BLUESKY_POLL_TIME_FILE).strip())
    except Exception as e:
        if not pkio.exception_is_not_found(e):
            raise
        t = sirepo.simulation_db.read_json(
            run_dir.join(template_common.INPUT_BASE_NAME),
        ).models.pollBlueskyForScansAnimation.start

    s = []
    for k, v in catalog().search({'time': {'$gte': t}}).items():
        t = max(t, v.metadata['start']['time'])
        s.append(_scan_info(k, metadata=v.metadata))
    pkio.atomic_write(_BLUESKY_POLL_TIME_FILE, t)
    return r.pkupdate(**_scan_info_result(s).data)


def catalog():
    return databroker.catalog[_CATALOG_NAME]


def stateless_compute_metadata(data):
    return PKDict(data=_metadata(data))


def stateless_compute_scan_info(data):
    return _scan_info_result([_scan_info(s) for s in data.scans])


def stateless_compute_scans(data):
    s = []
    for i, v in enumerate(catalog().search(databroker.queries.TimeRange(
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
        _generate_parameters_file(data, run_dir),
    )


def _dir_for_scan_uuid(scan_uuid):
    return sirepo.feature_config.cfg().raydata_data_dir.join(
        sirepo.util.safe_path(scan_uuid),
    )



def _generate_parameters_file(data, run_dir):
    if data.get('report') == 'pollBlueskyForScansAnimation':
        return template_common.render_jinja(
            SIM_TYPE,
            PKDict(time=data.models.pollBlueskyForScansAnimation.minutes * 60),
            'poll_bluesky.py'
        )
    s = _parse_scan_uuid(data)
    m = run_dir.join(_SIM_DATA.lib_file_name_with_model_field(
                'inputFiles',
                'mask',
                data.models.inputFiles.mask,
        )) if data.models.inputFiles.mask else ''
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(
            input_name=run_dir.join(data.models.analysisAnimation.notebook),
            mask_path=m,
            output_name=_OUTPUT_FILE,
            scan_dir=_dir_for_scan_uuid(s),
            scan_uuid=s,
        ),
    )


def _metadata(data):
    res = PKDict()
    for k in _METDATA[data.category]:
        res[
            ' '.join(k.split('_'))
        ] = catalog()[data.uid].metadata['start'][k]
    return res


def _scan_info(scan_uuid, metadata=None):
    m = metadata
    if not m:
        m =  catalog()[scan_uuid].metadata
    return PKDict(
        uid=scan_uuid,
        suid=_suid(scan_uuid),
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


def _parse_scan_uuid(data):
    return data.report

def _suid(scan_uuid):
    return scan_uuid.split('-')[0]
