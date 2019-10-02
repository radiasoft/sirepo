# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls.init_models(
            dm,
            (
                'beamAnimation',
                'beamHistogramAnimation',
                'parameterAnimation',
                'particleAnimation',
            ),
        )
        dm.solenoid.setdefault('solenoidFile', '')
#TODO(robnagler) setdefaults?
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
