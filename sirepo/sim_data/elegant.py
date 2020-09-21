# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
from sirepo.template.lattice import LatticeUtil
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        s = cls.schema()
        dm = data.models
        cls._init_models(dm, ('bunchSource', 'simulation', 'twissReport'))
        dm.setdefault('bunchFile', PKDict(sourceFile=None))
        dm.setdefault('rpnVariables', [])
        if 'commands' not in dm:
            dm.commands = cls.__create_commands(data)
            for m in dm.elements:
                model_schema = s.model[m.type]
                for k in m:
                    if k in model_schema and model_schema[k][1] == 'OutputFile' and m[k]:
                        m[k] = "1"
        for m in dm.elements:
            if m.type == 'WATCH':
                m.filename = '1'
                if m.mode == 'coordinates' or m.mode == 'coord':
                    m.mode = 'coordinate'
            cls.update_model_defaults(m, m.type)
        if 'centroid' not in dm.bunch:
            b = dm.bunch
            for f in 'emit_x', 'emit_y', 'emit_z':
                if b[f] and not isinstance(b[f], str):
                    b[f] /= 1e9
            if b.sigma_s and not isinstance(b.sigma_s, str):
                b.sigma_s /= 1e6
            c = cls.__find_first_bunch_command(data)
            # first_bunch_command may not exist if the elegant sim has no bunched_beam command
            if c:
                c.symmetrize = str(c.symmetrize)
                for f in s.model.bunch:
                    if f not in b and f in c:
                        b[f] = c[f]
            else:
                dm.bunch.centroid = '0,0,0,0,0,0'
        cls._init_models(dm, ('bunch', ))
        for m in dm.commands:
            cls.update_model_defaults(m, 'command_{}'.format(m._type))
        cls._organize_example(data)

    @classmethod
    def elegant_max_id(cls, data):
        max_id = 1
        for model_type in 'elements', 'beamlines', 'commands':
            if model_type not in data.models:
                continue
            for m in data.models[model_type]:
                i = m._id if '_id' in m else m.id
                if i > max_id:
                    max_id = i
        return max_id

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        if compute_model in ('twissReport', 'bunchReport'):
            res += ['bunch', 'bunchSource', 'bunchFile']
        if r == 'twissReport':
            res += ['elements', 'beamlines', 'commands', 'simulation.activeBeamlineId']
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if 'bunchReport' in analysis_model:
            return 'bunchReport'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = LatticeUtil(data, cls.schema()).iterate_models(lattice.InputFileIterator(cls)).result
        if data.models.bunchFile.sourceFile:
            res.append(cls.lib_file_name_with_model_field('bunchFile', 'sourceFile', data.models.bunchFile.sourceFile))
        return res

    @classmethod
    def __create_command(cls, name, data):
        s = cls.schema().model[name]
        for k in s:
            if k not in data:
                data[k] = s[k][2]
        return data

    @classmethod
    def __create_commands(cls, data):
        i = cls.elegant_max_id(data)
        b = data.models.bunch
        res = []
        for x in (
            PKDict(
                m='command_run_setup',
                _type='run_setup',
                centroid='1',
                concat_order=2,
                lattice='Lattice',
                output='1',
                p_central_mev=b.p_central_mev,
                parameters='1',
                print_statistics='1',
                sigma='1',
                use_beamline=data.models.simulation.get('visualizationBeamlineId', ''),
            ),
            PKDict(
                m='command_run_control',
                _type='run_control',
            ),
            PKDict(
                m='command_twiss_output',
                _type='twiss_output',
                filename='1',
            ),
            PKDict(
                m='command_bunched_beam',
                _type='bunched_beam',
                alpha_x=b.alpha_x,
                alpha_y=b.alpha_y,
                alpha_z=b.alpha_z,
                beta_x=b.beta_x,
                beta_y=b.beta_y,
                beta_z=b.beta_z,
                distribution_cutoff='3, 3, 3',
                enforce_rms_values='1, 1, 1',
                emit_x=b.emit_x / 1e09,
                emit_y=b.emit_y / 1e09,
                emit_z=b.emit_z,
                n_particles_per_bunch=b.n_particles_per_bunch,
                one_random_bunch='0',
                sigma_dp=b.sigma_dp,
                sigma_s=b.sigma_s / 1e06,
                symmetrize='1',
                Po=0.0,
            ),
            PKDict(
                m='command_track',
                _type='track',
            ),
        ):
            m = x[m]
            del x[m]
            i += 1
            x._id = i
            res.append(cls.__create_command(m, x))
        return res

    @classmethod
    def __find_first_bunch_command(cls, data):
        for m in data.models.commands:
            if m._type == 'bunched_beam':
                return m
        return None
