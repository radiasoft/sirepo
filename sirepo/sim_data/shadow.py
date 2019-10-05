# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    _ANALYSIS_ONLY_FIELDS = ['colorMap', 'notes', 'aspectRatio']

    @classmethod
    def compute_job_fields(cls, data):
        from sirepo.template import template_common

        r = data['report']
        res = cls._fields_for_compute(data, r) + [
            'bendingMagnet',
            'electronBeam',
            'geometricSource',
            'rayFilter',
            'simulation.istar1',
            'simulation.npoint',
            'simulation.sourceType',
            'sourceDivergence',
            'wiggler',
        ]
        if r == 'initialIntensityReport' and len(data['models']['beamline']):
            res.append([data['models']['beamline'][0]['position']])
        #TODO(pjm): only include items up to the current watchpoint
        if _SIM_DATA.is_watchpoint(r):
            res.append('beamline')
        for f in template_common.lib_files(data):
            res.append(f.mtime())
        return res

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        if (
            float(data.fixup_old_version) < 20170703.000001
            and 'geometricSource' in dm
        ):
            g = data.models.geometricSource
            x = g.cone_max
            g.cone_max = g.cone_min
            g.cone_min = x
        cls._init_models(dm, ('initialIntensityReport', 'plotXYReport'))
        for m in dm:
            if cls.is_watchpoint(m):
                cls.update_model_defaults(dm[m], 'watchpointReport')
        cls._organize_example(data)
