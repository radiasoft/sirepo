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
        dm.setdefault(
            'dicomEditorState', PKDict(),
            'doseCalculation', PKDict(selectedPTV='', selectedOARs=[]),
            'dicomDose', PKDict(frameCount=0),
            'dicomAnimation4', PKDict(
                dicomPlane='t',
                startTime=dm.dicomAnimation.get('startTime', 0),
            ),
            'dvhReport', PKDict(roiNumber=''),
        )
        if 'dvhType' not in dm.dvhReport:
            dm.dvhReport.update(
                dvhType='cumulative',
                dvhVolume='relative',
            )
        x = dm.dvhReport
        if 'roiNumbers' not in x and x.get('roiNumber', None):
            x.roiNumbers = [x.roiNumber]
            del x['roiNumber']
        dm.dicomAnimation4.setdefault('doseTransparency', 56)
