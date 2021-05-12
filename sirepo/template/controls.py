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
from sirepo.template.lattice import LatticeUtil
import copy
import csv
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.madx

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_SUMMARY_CSV_FILE = 'summary.csv'


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
            elementValues=_read_summary_line(run_dir)
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        elementValues=_read_summary_line(
            run_dir,
            SCHEMA.constants.maxBPMPoints,
        )
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


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _add_monitor(data):
    if list(filter(lambda el: el.type == 'MONITOR', data.models.elements)):
        return
    m = PKDict(
        _id=LatticeUtil.max_id(data) + 1,
        name='M_1',
        type='MONITOR',
    )
    data.models.elements.append(m)
    assert len(data.models.beamlines) == 1, \
        f'expecting 1 beamline={data.models.beamlines}'
    data.models.beamlines[0]['items'].append(m._id)


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
            _id=LatticeUtil.max_id(data) + 1,
            _type='select',
            flag='twiss',
            column='name,keyword,s,x,y',
        ),
        by_name.twiss or PKDict(
            _id=LatticeUtil.max_id(data) + 2,
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
    v.optimizerTargets = data.models.optimizerSettings.targets
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
        elif el.type == 'MONITOR':
            header += [_format_header(el._id, x) for x in ('x', 'y')]
        elif el.type == 'HMONITOR':
            header += [_format_header(el._id, 'x')]
        elif el.type == 'VMONITOR':
            header += [_format_header(el._id, 'y')]
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
    _unique_madx_elements(d)
    _add_monitor(d)
    sirepo.template.madx.eval_code_var(d)
    return PKDict(
        externalLattice=d,
        optimizerSettings=_SIM_DATA.default_optimizer_settings(d.models),
    )


def _read_summary_line(run_dir, line_count=None):
    path = run_dir.join(_SUMMARY_CSV_FILE)
    if not path.exists():
        return None
    header = None
    rows = []
    with open(str(path)) as f:
        reader = csv.reader(f)
        for row in reader:
            if header == None:
                header = row
                if not line_count:
                    break
            else:
                rows.append(row)
                if len(rows) > line_count:
                    rows.pop(0)
    if line_count:
        res = []
        for row in rows:
            res.append(PKDict(zip(header, row)))
        return res
    line = template_common.read_last_csv_line(path)
    if header and line:
        line = line.split(',')
        if len(header) == len(line):
            return [PKDict(zip(header, line))]
    return None


def _unique_madx_elements(data):
    def _do_unique(elem_ids):
        element_map = PKDict({e._id: e for e in data.models.elements})
        names = set([e.name for e in data.models.elements])
        max_id = LatticeUtil.max_id(data)
        res = []
        for el_id in elem_ids:
            if el_id not in res:
                res.append(el_id)
                continue
            el = copy.deepcopy(element_map[el_id])
            el.name = _unique_name(el.name, names)
            max_id += 1
            el._id = max_id
            data.models.elements.append(el)
            res.append(el._id)
        return res

    def _reduce_to_elements(beamline_id):
        def _do(beamline_id, res=None):
            if res is None:
                res = []
            for item_id in beamline_map[beamline_id]['items']:
                item_id = abs(item_id)
                if item_id in beamline_map:
                    _do(item_id, res)
                else:
                    res.append(item_id)
            return res

        return _do(beamline_id)

    def _remove_unused_elements(items):
        res = []
        for el in data.models.elements:
            if el._id in items:
                res.append(el)
        data.models.elements = res

    def _unique_name(name, names):
        assert name in names
        count = 2
        m = re.search(r'(\d+)$', name)
        if m:
            count = int(m.group(1))
            name = re.sub(r'\d+$', '', name)
        while f'{name}{count}' in names:
            count += 1
        names.add(f'{name}{count}')
        return f'{name}{count}'

    beamline_map = PKDict({
        b.id: b for b in data.models.beamlines
    })
    b = beamline_map[data.models.simulation.visualizationBeamlineId]
    b['items'] = _reduce_to_elements(b.id)
    _remove_unused_elements(b['items'])
    b['items'] = _do_unique(b['items'])
    data.models.beamlines = [b]
