# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        for m in cls.schema().model:
            # don't include beamline element models (all uppercase)
            if m == m.upper():
                continue
            if m not in dm:
                dm[m] = PKDict()
            cls.update_model_defaults(dm[m], m)
        for m in 'analysisAnimation', 'fitter', 'fitReport':
            if m in data.models:
                del data.models[m]
        dm.analysisReport.pksetdefault(history=[])
        dm.hiddenReport.pksetdefault(subreports=[])
        if 'beamlines' not in dm:
            cls._init_default_beamline(data)
        for e in dm.elements:
            # create a watchpointReport for each WATCH element
            if e.type == 'WATCH':
                n = 'watchpointReport{}'.format(e._id)
                if n not in dm:
                    dm[n] = m = PKDict(_id=e._id)
                    cls.update_model_defaults(m, 'watchpointReport')
        cls._organize_example(data)

    @classmethod
    def webcon_analysis_data_file(cls, data):
        return cls.lib_file_name_with_model_field('analysisData', 'file', data.models.analysisData.file)

    @classmethod
    def webcon_analysis_report_name_for_fft(cls, data):
        return data.models[data.report].get('analysisReport', 'analysisReport')

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = [
            r,
            'analysisData',
        ]
        if 'fftReport' in r:
            n = cls.webcon_analysis_report_name_for_fft(data)
            res += ['{}.{}'.format(n, v) for v in ('x', 'y1', 'history')]
        if 'watchpointReport' in r or r in ('correctorSettingReport', 'beamPositionReport'):
            # always recompute the EPICS reports
            res.append([cls._force_recompute()])
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == 'epicsServerAnimation':
            return analysis_model
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        r = data.get('report')
        if r == 'epicsServerAnimation':
            res += [
                'beam_line_example.db',
                'epics-boot.cmd',
            ]
        elif data.models.analysisData.get('file'):
            res.append(cls.webcon_analysis_data_file(data))
        return res

    @classmethod
    def _init_default_beamline(cls, data):
        #TODO(pjm): hard-coded beamline for now, using elegant format
        data.models.elements = [
                PKDict(
                    _id=8,
                    l=0.1,
                    name='drift',
                    type='DRIF'
                ),
                PKDict(
                    _id=10,
                    hkick=0,
                    name='HV_KICKER_1',
                    type='KICKER',
                    vkick=0
                ),
                PKDict(
                    _id=12,
                    hkick=0,
                    name='HV_KICKER_2',
                    type='KICKER',
                    vkick=0
                ),
                PKDict(
                    _id=13,
                    hkick=0,
                    name='HV_KICKER_3',
                    type='KICKER',
                    vkick=0
                ),
                PKDict(
                    _id=14,
                    hkick=0,
                    name='HV_KICKER_4',
                    type='KICKER',
                    vkick=0
                ),
                PKDict(
                    _id=24,
                    k1=-5,
                    l=0.05,
                    name='F_QUAD_1',
                    type='QUAD',
                ),
                PKDict(
                    _id=25,
                    k1=5,
                    l=0.05,
                    name='D_QUAD_1',
                    type='QUAD',
                ),
                PKDict(
                    _id=30,
                    k1=-5,
                    l=0.05,
                    name='F_QUAD_2',
                    type='QUAD',
                ),
                PKDict(
                    _id=31,
                    k1=5,
                    l=0.05,
                    name='D_QUAD_2',
                    type='QUAD',
                ),
                PKDict(
                    _id=9,
                    name='BPM_1',
                    type='WATCH',
                    filename='1',
                ),
                PKDict(
                    _id=27,
                    name='BPM_2',
                    type='WATCH',
                    filename='1',
                ),
                PKDict(
                    _id=28,
                    name='BPM_3',
                    type='WATCH',
                    filename='1',
                ),
                PKDict(
                    _id=29,
                    name='BPM_4',
                    type='WATCH',
                    filename='1',
                )
        ]
        data.models.beamlines = [
            PKDict(
                id=1,
                items=[
                    8, 8, 10, 8, 8, 9, 8, 8,
                    8, 8, 12, 8, 8, 27, 8, 8,
                    8, 24, 8, 8, 25, 8,
                    8, 8, 13, 8, 8, 28, 8, 8,
                    8, 8, 14, 8, 8, 29, 8, 8,
                    8, 30, 8, 8, 31, 8,
                ],
                name='beamline',
            ),
        ]
