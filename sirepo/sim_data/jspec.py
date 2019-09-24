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
        cls.init_models(dm, ('ring', 'particleAnimation', 'twissReport'))
        if 'coolingRatesAnimation' not in dm:
            for m in ('beamEvolutionAnimation', 'coolingRatesAnimation'):
                dm[m] = PKDict()
                cls.update_model_defaults(dm[m], m)
        if 'beam_type' not in dm.ionBeam:
            dm.ionBeam.setdefault(
                'beam_type',
                'bunched' if dm.ionBeam.rms_bunch_length > 0 else 'continuous',
            )
        if 'beam_type' not in dm.electronBeam:
            x = dm.electronBeam
            x.beam_type = 'continuous' if x.shape == 'dc_uniform' else 'bunched'
            x.rh = x.rv = 0.004
        x = dm.simulationSettings
        if x.model == 'model_beam':
            x.model = 'particle'
        if 'ibs' not in x:
            x.ibs = '1'
            x.e_cool = '1'
        if not x.get('ref_bet_x', None):
            x.ref_bet_x = x.ref_bet_y = 10
            for f in (
                'ref_alf_x',
                'ref_disp_x',
                'ref_disp_dx',
                'ref_alf_y',
                'ref_disp_y',
                'ref_disp_dy',
            ):
                x[f] = 0
        # if model field value is less than min, set to default value
        s = cls.schema()
        for m in dm:
            x = dm[m]
            if m in s.model:
                for f in s.model[m]:
                    d = s.model[m][f]
                    if len(d) > 4 and x[f] < d[4]:
                        x[f] = d[2]
        cls.organize_example(data)
