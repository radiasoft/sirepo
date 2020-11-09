# -*- coding: utf-8 -*-
u"""Controls execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import copy
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.lattice
import sirepo.template.madx

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        monitorValues=sirepo.template.madx.extract_monitor_values(run_dir),
    )


def get_application_data(data, **kwargs):
    if data.method == 'get_madx_sim_list':
        res = []
        for f in pkio.sorted_glob(
            _SIM_DATA.controls_madx_dir().join(
                '*',
                sirepo.simulation_db.SIMULATION_DATA_FILE,
            ),
        ):
            m = sirepo.simulation_db.read_json(f).models
            res.append(PKDict(
                name=m.simulation.name,
                simulationId=m.simulation.simulationId,
            ))
        return PKDict(simList=res)
    elif data.method == 'get_external_lattice':
        return _get_external_lattice(data.simulationId)
    raise AssertionError(f'unknown application data method={data.method}')

def python_source_for_model(data, model):
    return sirepo.template.madx.python_source_for_model(data.models.externalLattice, model)


def write_parameters(data, run_dir, is_parallel):
    data.models.externalLattice.report = ''
    sirepo.template.madx.write_parameters(data.models.externalLattice, run_dir, is_parallel)


def _dedup_elements(data):
    def _reduce_to_elements(beamline_id):
        def _do(beamline_id):
            for i, item_id in enumerate(beamline_map[beamline_id]['items']):
                item_id = abs(item_id)
                if item_id in beamline_map:
                    _do(item_id)
                    continue
                res.append(item_id)

        res = []
        _do(beamline_id)
        return res

    def _do_dedup(elem_ids):
        nonlocal max_id

        res = []
        for i, e in enumerate(elem_ids):
            l = data.models.elements[element_map[e]]
            if e not in res:
                res.append(e)
                _set_element_name(l, i)
                continue
            n = copy.deepcopy(l)
            _set_element_name(l, i)
            max_id += 1
            n._id = max_id
            data.models.elements.append(n)
            res.append(n._id)
        return res

    def _set_element_name(elem, index):
        elem['name'] = f'{elem.type[0]}{index}'


    max_id = sirepo.template.lattice.LatticeUtil.max_id(data)
    beamline_map = PKDict(
        {
            e.id: PKDict(
                items=e['items'],
                index=i,
            ) for i, e in enumerate(data.models.beamlines)
        },
    )
    element_map = PKDict({e._id: i for i, e in enumerate(data.models.elements)})
    a = data.models.simulation.visualizationBeamlineId
    b = data.models.beamlines[beamline_map[a].index]
    b['items'] = _do_dedup(_reduce_to_elements(a))
    data.models.beamlines = [b]


def _delete_unused_commands(data):
    import sirepo.template.lattice

    for c in list(data.models.commands):
        if f'{sirepo.template.lattice.LatticeParser.COMMAND_PREFIX}{c._type}' \
            not in _SCHEMA.model.keys():
            data.models.commands.remove(c)


def _delete_unused_models(data):
    for m in list(data.models.keys()):
        if m not in [
                *_SCHEMA.model.keys(),
                'beamlines',
                'commands',
                'elements',
                'report',
                'rpnCache',
                'rpnVariables',
        ]:
            data.models.pkdel(m)


def _get_external_lattice(simulation_id):
    d = sirepo.simulation_db.read_json(
        _SIM_DATA.controls_madx_dir().join(
            simulation_id,
            sirepo.simulation_db.SIMULATION_DATA_FILE,
        ),
    )
    _delete_unused_models(d)
    _delete_unused_commands(d)
    _dedup_elements(d)
    return PKDict(d)
