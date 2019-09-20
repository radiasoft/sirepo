# -*- coding: utf-8 -*-
u"""hellweg simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        for m in (
            'beamAnimation',
            'beamHistogramAnimation',
            'parameterAnimation',
            'particleAnimation',
        ):
            if m not in dm:
                dm[m] = pkcollections.Dict()
            cls.update_model_defaults(dm[m], m, _SCHEMA)
        if 'solenoidFile' not in dm.solenoid:
            dm.solenoid.solenoidFile = ''
        if 'beamDefinition' not in dm.beam:
            dm.beam.update(
                beamDefinition='transverse_longitude',
                cstCompress='0',
                transversalFile2d='',
                transversalFile4d='',
                longitudinalFile1d='',
                longitudinalFile2d='',
                cstFile='',
            )
        cls.organize_example(data)
