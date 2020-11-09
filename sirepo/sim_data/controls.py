# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.lattice import LatticeUtil
import sirepo.sim_data
import sirepo.simulation_db

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def controls_madx_dir(cls):
        return sirepo.simulation_db.simulation_dir('madx')

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        sirepo.sim_data.get_class('madx').fixup_old_data(dm.externalLattice)
        cls._init_models(
            dm,
            (
                'command_beam',
                'command_twiss',
                'dataFile',
            ),
        )
        dm.externalLattice.models.bunch.beamDefinition = 'pc'
        twiss = LatticeUtil.find_first_command(dm.externalLattice, 'twiss')
        twiss.file = '1'
        dm.command_beam.update(LatticeUtil.find_first_command(dm.externalLattice, 'beam'))
        dm.command_twiss.update(twiss)


    @classmethod
    def _lib_file_basenames(cls, data):
        return []
