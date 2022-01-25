# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.lattice import LatticeUtil
from sirepo.template.template_common import ParticleEnergy
import math
import re
import sirepo.sim_data
import sirepo.simulation_db


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def beamline_elements(cls, madx):
        elmap = PKDict({e._id: e for e in madx.elements})
        for el_id in madx.beamlines[0]['items']:
            yield elmap[el_id]

    @classmethod
    def controls_madx_dir(cls):
        return sirepo.simulation_db.simulation_dir('madx')

    @classmethod
    def current_field(cls, kick_field):
        return 'current_{}'.format(kick_field)

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
        # pkdp('\n\n\n\n\n data models: {} \n\n\n\n\n --', dm)
        # pkdp('\n\n\n\n\n externalLattice in dm? : {} \n\n\n\n\n --', 'externalLattice' in dm)
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
            if 'controlSettings' not in dm:
                cls.init_process_variables(dm)
                cls.init_currents(dm.command_beam, dm.externalLattice.models)
            if 'inputs' not in dm.optimizerSettings:
                dm.optimizerSettings.inputs = PKDict(
                    kickers=PKDict(),
                    quads=PKDict()
                )
                for el in cls.beamline_elements(dm.externalLattice.models):
                    if el.type == 'QUADRUPOLE':
                        dm.optimizerSettings.inputs.quads[str(el._id)] = False
                    elif 'KICKER' in el.type:
                        dm.optimizerSettings.inputs.kickers[str(el._id)] = True
        if dm.command_beam.gamma == 0 and 'pc' in dm.command_beam and dm.command_beam.pc > 0:
            cls.update_beam_gamma(dm.command_beam)
            dm.command_beam.pc = 0

    @classmethod
    def init_currents(cls, beam, models):
        def is_kick_field(field):
            return re.search(r'^(.?kick|k1)$', field)
        ac = AmpConverter(beam)
        for el in cls.beamline_elements(models):
            for f in list(el.keys()):
                if is_kick_field(f):
                    el[cls.current_field(f)] = ac.kick_to_current(el[f])

    @classmethod
    def init_process_variables(cls, models):
        pvs = []
        def _add_pv(elId, dim, write='0'):
            pvs.append(PKDict(
                elId=elId,
                pvDimension=dim,
                isWritable=write,
                pvName='',
            ))
        models.controlSettings = cls.model_defaults('controlSettings').pkupdate({
            'processVariables': pvs,
        })
        for el in cls.beamline_elements(models.externalLattice.models):
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
        return models

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
            res = ['controlSettings', 'dataFile', 'externalLattice']
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if 'instrument' in analysis_model:
            return 'instrumentAnimation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        return []


class AmpConverter():
    _GEV_TO_KG = 5.6096e26
    _DEFAULT_FACTOR = 100
    # Coulomb
    _ELEMENTARY_CHARGE = 1.602e-19
    _SCHEMA = SimData.schema()

    def __init__(self, beam, amp_table=None):
        if amp_table and len(amp_table[0]) < 2:
            raise AssertionError('invalid amp_table: {}'.format(amp_table))
        self._computed_reverse_table = False
        self._amp_table = amp_table
        self._beam_info = self.__beam_info(beam)

    def build_reverse_map(self):
        if self._computed_reverse_table:
            return self._amp_table
        table = self._amp_table
        if table:
            for row in table:
                k = self.__compute_kick(row[0], row[1])
                if len(row) > 2:
                    row[2] = k
                else:
                    row.append(k)
        self._computed_reverse_table = True
        return table

    def current_to_kick(self, current):
        return self.__compute_kick(
            current,
            self.__interpolate_table(current, 0, 1))

    def kick_to_current(self, kick):
        self.build_reverse_map()
        return self.__compute_current(
            float(kick),
            self.__interpolate_table(kick, 2, 1))

    def __beam_info(self, beam):
        if beam.get('particle') and self._SCHEMA.constants.particleMassAndCharge.get(beam.particle):
            pmc = self._SCHEMA.constants.particleMassAndCharge.get(beam.particle)
        else:
            pmc = [beam.mass, beam.charge]
        return PKDict(
            mass=pmc[0] / self._GEV_TO_KG,
            charge=pmc[1] * self._ELEMENTARY_CHARGE,
            gamma=beam.gamma,
            beta=math.sqrt(1 - (1 / (beam.gamma * beam.gamma))),
        )

    def __compute_current(self, kick, factor):
        b = self._beam_info
        return kick * b.gamma * b.mass * b.beta * self._SCHEMA.constants.clight \
            / (b.charge * factor)

    def __compute_kick(self, current, factor):
        b = self._beam_info
        return current * b.charge * factor \
            / (b.gamma * b.mass * b.beta * self._SCHEMA.constants.clight)

    def __interpolate_table(self, value, from_index, to_index):
        table = self._amp_table
        if not table:
            return self._DEFAULT_FACTOR
        if len(table) == 1 or value < table[0][from_index]:
            return table[0][to_index]
        i = 1
        while i < len(table):
            if table[i][from_index] > value:
                return (value - table[i-1][from_index]) / (table[i][from_index] - table[i-1][from_index]) \
                    * (table[i][to_index] - table[i-1][to_index]) + table[i-1][to_index]
            i += 1
        return table[-1][to_index]
