# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.lattice import LatticeUtil
from sirepo.template.template_common import ParticleEnergy
import sirepo.sim_data
import sirepo.simulation_db

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def controls_madx_dir(cls):
        return sirepo.simulation_db.simulation_dir('madx')

    @classmethod
    def beamline_elements(cls, madx):
        elmap = PKDict({e._id: e for e in madx.elements})
        for el_id in madx.beamlines[0]['items']:
            yield elmap[el_id]

    @classmethod
    def default_optimizer_settings(cls, madx):
        targets = []
        for el in cls.beamline_elements(madx):
            if el.type in ('MONITOR', 'HMONITOR', 'VMONITOR'):
                item = cls.model_defaults('optimizerTarget')
                item.name = el.name
                if el.type == 'HMONITOR':
                    del item['y']
                elif el.type == 'VMONITOR':
                    del item['x']
                targets.append(item)
        return cls.model_defaults('optimizerSettings').pkupdate(PKDict(
            targets=targets,
        ))

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            (
                'command_beam',
                'command_twiss',
                'dataFile',
                'initialMonitorPositionsReport',
            ),
        )
        if 'externalLattice' in dm:
            sirepo.sim_data.get_class('madx').fixup_old_data(dm.externalLattice)
            if 'optimizerSettings' not in dm:
                dm.optimizerSettings = cls.default_optimizer_settings(dm.externalLattice.models)
            if 'processVariables' not in dm:
                cls.init_process_variables(data)
        if dm.command_beam.gamma == 0 and 'pc' in dm.command_beam and dm.command_beam.pc > 0:
            cls.update_beam_gamma(dm.command_beam)
            dm.command_beam.pc = 0

    @classmethod
    def init_process_variables(cls, data):
        pvs = []
        def _add_pv(elId, dim, write='0'):
            pvs.append(PKDict(
                elId=elId,
                pvDimension=dim,
                isWritable=write,
                pvName='',
            ))
        data.models.processVariables = PKDict(
            variables=pvs,
        )
        for el in cls.beamline_elements(data.models.externalLattice.models):
            if el.type == 'MONITOR':
                _add_pv(el._id, 'horizontal')
                _add_pv(el._id, 'vertical')
            elif el.type == 'HMONITOR':
                _add_pv(el._id, 'horizontal')
            elif el.type == 'VMONITOR':
                _add_pv(el._id, 'vertical')
            elif el.type == 'KICKER':
                _add_pv(el._id, 'horizontal')
                _add_pv(el._id, 'horizontal', '1')
                _add_pv(el._id, 'vertical')
                _add_pv(el._id, 'vertical', '1')
            elif el.type == 'HKICKER':
                _add_pv(el._id, 'horizontal')
                _add_pv(el._id, 'horizontal', '1')
            elif el.type == 'VKICKER':
                _add_pv(el._id, 'vertical')
                _add_pv(el._id, 'vertical', '1')
            elif el.type == 'QUADRUPOLE':
                _add_pv(el._id, 'none')
        return data

    @classmethod
    def update_beam_gamma(cls, beam):
        beam.gamma = ParticleEnergy.compute_energy(
            'madx',
            beam.particle,
            beam,
        ).gamma

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        if r == 'initialMonitorPositionsReport':
            res = ['dataFile', 'externalLattice']
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
