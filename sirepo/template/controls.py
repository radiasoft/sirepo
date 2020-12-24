# -*- coding: utf-8 -*-
u"""Controls execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo.template import template_common
import copy
import csv
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.lattice
import sirepo.template.madx

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()
_SUMMARY_CSV_FILE = 'summary.csv'


def background_percent_complete(report, run_dir, is_running):
    v = _read_summary_line(run_dir)
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
            elementValues=v,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        elementValues=v,
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
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _dedup_madx_elements(data):
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


def _delete_unused_madx_commands(data):
    # remove all commands except first beam and twiss
    by_name = PKDict(
        beam=None,
        twiss=None,
    )
    for c in data.models.commands:
        if c._type in by_name and not by_name[c._type]:
            by_name[c._type] = c
    if by_name.twiss:
        by_name.twiss.sectorfile = '0'
        by_name.twiss.sectormap = '0'
        by_name.twiss.file = '1';
    data.models.commands = [
        by_name.beam,
        PKDict(
            _id=sirepo.template.lattice.LatticeUtil.max_id(data) + 1,
            _type='select',
            flag='twiss',
            column='name,keyword,s,x,y',
        ),
        by_name.twiss or PKDict(
            _id=sirepo.template.lattice.LatticeUtil.max_id(data) + 2,
            _type='twiss',
            file='1',
        )
    ]


def _delete_unused_madx_models(data):
    for m in list(data.models.keys()):
        if m not in [
            'beamlines',
            'bunch',
            'commands',
            'elements',
            'report',
            'rpnVariables',
            'simulation',
        ]:
            data.models.pkdel(m)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    _generate_madx(v, data)
    v.summaryCSV = _SUMMARY_CSV_FILE
    return res + template_common.render_jinja(SIM_TYPE, v)


def _generate_madx(v, data):

    def _format_header(el_id, field):
        return f'el_{el_id}.{field}'

    def _set_opt(el, field, kicker):
        count = len(kicker.kick)
        kicker.kick.append(el[field])
        el[field] = '{' + f'sr_opt{count}' + '}'
        kicker.header.append(_format_header(el._id, field))

    kicker = PKDict(
        header=[],
        kick=[],
    )
    madx = data.models.externalLattice.models
    header = []
    element_map = PKDict({e._id: e for e in madx.elements})
    for el_id in madx.beamlines[0]['items']:
        el = element_map[el_id]
        if el.type == 'KICKER':
            _set_opt(el, 'hkick', kicker)
            _set_opt(el, 'vkick', kicker)
        elif el.type in ('HKICKER', 'VKICKER'):
            _set_opt(el, 'kick', kicker)
        elif 'MONITOR' in el.type:
            header += [_format_header(el._id, x) for x in ('x', 'y')]
    v.summaryCSVHeader = ','.join(kicker.header + header)
    v.correctorCount = len(kicker.kick)
    v.monitorCount = len(header) / 2
    data.models.externalLattice.report = ''
    v.madxSource = sirepo.template.madx.generate_parameters_file(data.models.externalLattice)


def _get_external_lattice(simulation_id):
    d = sirepo.simulation_db.read_json(
        _SIM_DATA.controls_madx_dir().join(
            simulation_id,
            sirepo.simulation_db.SIMULATION_DATA_FILE,
        ),
    )
    d.models.bunch.beamDefinition = 'pc';
    _delete_unused_madx_models(d)
    _delete_unused_madx_commands(d)
    _dedup_madx_elements(d)
    sirepo.template.madx.eval_code_var(d)
    return PKDict(d)


def _read_summary_line(run_dir):
    path = run_dir.join(_SUMMARY_CSV_FILE)
    if not path.exists():
        return None
    header = None
    with open(str(path)) as f:
        reader = csv.reader(f)
        for row in reader:
            header = row
            break
    line = template_common.read_last_csv_line(path)
    if header and line:
        line = line.split(',')
        if len(header) == len(line):
            return PKDict(zip(header, line))
    return None
