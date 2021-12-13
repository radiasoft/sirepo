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

_DEVICE_SERVER_PROPERTY_IDS = PKDict(
    HKICKER=PKDict(kick='propForHKick'),
    KICKER=PKDict(hkick='propForHKick', vkick='propForVKick'),
    VKICKER=PKDict(kick='propForHKick'),
)

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


def stateful_compute_get_madx_sim_list(data):
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
            invalidMsg=None if _has_kickers(m) else 'No beamlines' if not _has_beamline(m) else 'No kickers'
        ))
    return PKDict(simList=res)


def stateful_compute_get_external_lattice(data):
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
    data.models.bunch.beamDefinition = 'gamma';
    _SIM_DATA.update_beam_gamma(by_name.beam)
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
    if data.get('report') == 'initialMonitorPositionsReport':
        v.optimizerSettings_method = 'runOnce'
    return res + template_common.render_jinja(SIM_TYPE, v)


def _generate_madx(v, data):

    def _format_header(el_id, field):
        return f'el_{el_id}.{field}'

    def _handle_kicker(element):
        fields = ('hkick', 'vkick')
        if element.type in ('HKICKER', 'VKICKER'):
            fields = ('kick',)
        for f in fields:
            count = len(kicker.kick)
            kicker.kick.append(el[f])
            n = '{' + f'sr_opt{count}' + '}'
            el[f] = n
            kicker.header.append(_format_header(el._id, f))
            v.devices.append(PKDict(
                sr_opt=n,
                deviceName=el.deviceName,
                propId=_DEVICE_SERVER_PROPERTY_IDS[element.type][f]
            ))

    v.devices = []
    kicker = PKDict(
        header=[],
        kick=[],
    )
    madx = data.models.externalLattice.models
    header = []
    element_map = PKDict({e._id: e for e in madx.elements})
    for el_id in madx.beamlines[0]['items']:
        el = element_map[el_id]
        if el.type in ('KICKER', 'HKICKER', 'VKICKER'):
            _handle_kicker(el)
        elif el.type == 'MONITOR':
            header += [_format_header(el._id, x) for x in ('x', 'y')]
        elif el.type == 'HMONITOR':
            header += [_format_header(el._id, 'x')]
        elif el.type == 'VMONITOR':
            header += [_format_header(el._id, 'y')]
    v.summaryCSVHeader = ','.join(kicker.header + header)
    v.initialCorrectors = '[{}]'.format(','.join([str(x) for x in kicker.kick]))
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
    _delete_unused_madx_models(d)
    _delete_unused_madx_commands(d)
    sirepo.template.madx.uniquify_elements(d)
    _add_monitor(d)
    sirepo.template.madx.eval_code_var(d)
    return PKDict(
        externalLattice=d,
        optimizerSettings=_SIM_DATA.default_optimizer_settings(d.models),
    )


def _has_beamline(model):
    return model.elements and model.beamlines


def _has_kickers(model):
    if not _has_beamline(model):
        return False
    k_ids = [e._id for e in model.elements if 'KICKER' in e.type]
    if not k_ids:
        return False
    for b in model.beamlines:
        if any([item in k_ids for item in b['items']]):
            return True
    return False


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
