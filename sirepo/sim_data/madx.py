# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
from sirepo.template.lattice import LatticeUtil

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        if 'twissEllipseReport1' not in dm:
            for i in range(1, 3):
                m = dm['twissEllipseReport{}'.format(i)] = PKDict()
                cls.update_model_defaults(m, 'twissEllipseReport')
                m.dim = 'x' if i == 1 else 'y'
        if 'bunchReport1' not in dm:
            b_params = [('x', 'px'), ('y', 'py'), ('x', 'y'), ('z', 'pz')]
            for (i, p) in enumerate(b_params):
                m = dm['bunchReport{}'.format(i - 1)] = PKDict()
                cls.update_model_defaults(m, 'bunchReport')
                m.x = b_params[i][0]
                m.y = b_params[i][1]
        if 'initialTwissParams' not in dm:
            for dim in ['x', 'y']:
                m = dm['initialTwissParams'] = PKDict()
                cls.update_model_defaults(m, 'initialTwissParams')
                m.dim = dim
        if 'particleTracking' not in dm:
            m = dm['particleTracking'] = PKDict()
            cls.update_model_defaults(m, 'particleTracking')
        for container in ('commands', 'elements'):
            for m in dm[container]:
                cls.update_model_defaults(m, LatticeUtil.model_name_for_data(m))


    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        # TODO(e-carlin): impl
        if r == 'twissReport':
            return ['beamlines', 'elements', 'commands', 'simulation.activeBeamlineId', 'rpnVariables']
        return []

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        #if 'bunchReport' in analysis_model:
        #    return 'bunchReport'
        #if 'twissEllipseReport' in analysis_model:
        #    return 'twissEllipseReport'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        # TODO(e-carlin): impl
        return []
