# -*- coding: utf-8 -*-
u"""Flash Config parser.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog

def _fields(templates, values):
    # template: [field template, label template]
    # values: values to insert into the field/label templates
    return {
        t[0].format(v): t[1].format(v.upper()) for v in values for t in templates
    }

class SpecializedViews():
    _LABELS = PKDict(
        UnitSystem='System of Units',
        cfl='Courant Factor',
        eosMode='Eos Mode',
        eosModeInit='Initial Eos Mode',
        geometry='Grid Geometry',
        grav_boundary_type='Boundary Condition',
        lrefine_max='Maximum Refinement Level',
        lrefine_min='Minimum Refinement Level',
        refine_var_count='Refine Variable Count',
        threadHydroBlockList='Block List Threading',
        threadHydroWithinBlock='Within Block Threading',
        updateHydroFluxes='Update Hydro Fluxes',
        useGravity='Use Gravity',
        useHydro='Use Hydro Calculation',
        use_cma_advection='Use CMA Advection',
        use_cma_flattening='Use CMA Flattening',
        useFlame='Use Flame',
        **_fields([
            ['{}l_boundary_type', '{} Lower Boundary Type'],
            ['{}r_boundary_type', '{} Upper Boundary Type'],
            ['{}min', '{} Minimum'],
            ['{}max', '{} Maximum'],
            ['nblock{}', 'Blocks in {}'],
        ], ['x', 'y', 'z']),
        **_fields([
            ['refine_var_{}', 'Name Variable {}'],
            ['refine_cutoff_{}', 'Refine Variable {}'],
            ['derefine_cutoff_{}', 'Derefine Variable {}'],
        ], [str(v) for v in range(1, 7)]),
    )

    _VIEW_BY_NAME = PKDict(
        physics_sourceTerms_Flame=PKDict(
            advanced=[],
            basic=['useFlame'],
        ),
        Grid=PKDict(
            basic=[
                ['Main', [
                    'geometry',
                    'eosModeInit',
                    'eosMode',
                    [
                        ['X', [
                            'xl_boundary_type',
                            'xr_boundary_type',
                            'xmin',
                            'xmax'
                        ]],
                        ['Y', [
                            'yl_boundary_type',
                            'yr_boundary_type',
                            'ymin',
                            'ymax'
                        ]],
                        ['Z', [
                            'zl_boundary_type',
                            'zr_boundary_type',
                            'zmin',
                            'zmax'
                        ]]
                    ]
                ]],
                ['Paramesh', [
                    'Grid_paramesh.nblockx',
                    'Grid_paramesh.nblocky',
                    'Grid_paramesh.nblockz',
                    'Grid_paramesh.lrefine_min',
                    'Grid_paramesh.lrefine_max',
                    'Grid_paramesh.refine_var_count',
                    [
                        ['Name', [
                            'Grid_paramesh.refine_var_1',
                            'Grid_paramesh.refine_var_2',
                            'Grid_paramesh.refine_var_3',
                            'Grid_paramesh.refine_var_4'
                        ]],
                        ['Refine Cutoff', [
                            'Grid_paramesh.refine_cutoff_1',
                            'Grid_paramesh.refine_cutoff_2',
                            'Grid_paramesh.refine_cutoff_3',
                            'Grid_paramesh.refine_cutoff_4'
                        ]],
                        ['Derefine Cutoff', [
                            'Grid_paramesh.derefine_cutoff_1',
                            'Grid_paramesh.derefine_cutoff_2',
                            'Grid_paramesh.derefine_cutoff_3',
                            'Grid_paramesh.derefine_cutoff_4'
                        ]]
                    ]
                ]]
            ],
        ),
        physics_Gravity=PKDict(
            advanced=[],
            basic=[
                'useGravity',
                'grav_boundary_type'
            ],
        ),
        physics_Hydro=PKDict(
            advanced=[
                'threadHydroBlockList',
                'threadHydroWithinBlock',
                'updateHydroFluxes',
                'use_cma_advection',
                'use_cma_flattening',
            ],
            basic=[
                'useHydro',
                'cfl',
                'UnitSystem',
            ],
        ),
    )

    def update_schema(self, schema):
        self.__update_labels(schema)
        self.__update_views(schema)
        return schema

    def __update_labels(self, schema):
        for m in schema.model.values():
            for f in m:
                if f not in self._LABELS:
                    continue
                info = m[f]
                if len(info) == 3:
                    info.append(f)
                elif info[3]:
                    info[3] = '{} {}'.format(f, info[3])
                else:
                    info[3] = f
                info[0] = self._LABELS[f]

    def __update_views(self, schema):
        for n, v in self._VIEW_BY_NAME.items():
            if n not in schema.view:
                continue
            for f in v:
                schema.view[n][f] = v[f]
