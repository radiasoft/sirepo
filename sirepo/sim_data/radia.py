# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import copy
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    ANALYSIS_ONLY_FIELDS = frozenset((
        'alpha',
        'bgColor',
        'color',
        'colorMap',
        'name',
        'notes',
        'scaling',
    ))

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = cls._non_analysis_fields(data, r) + []
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in (
            'solverAnimation',
            'reset'
        ):
            return 'solverAnimation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        return PKDict()

    @classmethod
    def fixup_old_data(cls, data):

        dm = data.models
        cls._init_models(
            dm,
            None,
            dynamic=lambda m: cls.__dynamic_defaults(data, m)
        )
        if dm.get('geometry'):
            dm.geometryReport = dm.geometry.copy()
            del dm['geometry']
        if dm.get('solver'):
            dm.solverAnimation = dm.solver.copy()
            del dm['solver']
        if not dm.fieldPaths.get('paths'):
            dm.fieldPaths.paths = []
        if dm.simulation.get('isExample'):
            if not dm.simulation.get('exampleName'):
                dm.simulation.exampleName = dm.simulation.name
            if dm.simulation.name == 'Wiggler':
                dm.geometryReport.isSolvable = '0'
                if not len(dm.fieldPaths.paths):
                    dm.fieldPaths.paths.append(PKDict(
                        _super='fieldPath',
                        begin='0, -225, 0',
                        end='0, 225, 0',
                        id= 0,
                        name='y axis',
                        numPoints=101,
                        type='line'
                    ))
        if dm.simulation.magnetType == 'undulator':
            cls._fixup_undulator(dm)
        for o in dm.geometryReport.objects:
            if o.get('model') == 'box':
                o.model = 'cuboid'
            if o.get('type') == 'box':
                o.type = 'cuboid'
            if not o.get('bevels'):
                o.bevels = []
            if not o.get('segments'):
                o.segments = o.get('division', '1, 1, 1')
        sch = cls.schema()
        for m in [m for m in dm if m in sch.model]:
            s_m = sch.model[m]
            for f in [
                f for f in s_m if f in dm[m] and s_m[f][1] == 'Boolean' and
                    not dm[m][f]
            ]:
                dm[m][f] = '0'
        cls._organize_example(data)

    @classmethod
    def _fixup_undulator(cls, dm):
        import sirepo.util

        if not dm.simulation.get('heightAxis'):
            dm.simulation.heightAxis = 'z'

        if dm.simulation.undulatorType in ('undulatorBasic'):
            return

        if 'hybridUndulator' in dm:
            dm.undulatorHybrid = copy.deepcopy(dm.hybridUndulator)
            del dm['hybridUndulator']
            dm.simulation.undulatorType = 'undulatorHybrid'

        u = dm.undulatorHybrid
        g = dm.geometryReport

        for (k, v) in PKDict(
            halfPole='Half Pole',
            magnet='Magnet Block',
            pole='Pole',
            corePoleGroup='Magnet-Pole Pair',
            terminationGroup='Termination',
            octantGroup='Octant'
        ).items():
            if k not in u:
                u[k] = sirepo.util.find_obj(g.objects, 'name', v)

        if not u.get('terminations'):
            u.terminations = []
        for i, t_id in enumerate(u.terminationGroup.members):
            t = u.terminations[i]
            if 'object' not in t:
                t.object = sirepo.util.find_obj(g.objects, 'id', t_id)
                cls.update_model_defaults(t, 'termination')


    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir, post_init=False):
        try:
            super().sim_files_to_run_dir(data, run_dir)
        except sirepo.sim_data.SimDbFileNotFound as e:
            if post_init:
                raise e

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if 'dmpImportFile' in data.models.simulation:
            res.append(f'{cls.schema().constants.radiaDmpFileType}.{data.models.simulation.dmpImportFile}')
        if 'fieldType' in data:
            res.append(cls.lib_file_name_with_model_field(
                'fieldPath',
                data.fieldType,
                data.name + '.' + data.fileType))
        return res

    @classmethod
    def _sim_file_basenames(cls, data):
        # TODO(e-carlin): share filename with template
        return [
            PKDict(basename='geometry.dat'),
            PKDict(basename='geometryReport.h5'),
        ]
