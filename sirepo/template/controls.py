# -*- coding: utf-8 -*-
u"""Controls execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo.sim_data.controls import AmpConverter
from sirepo.template import template_common
from sirepo.template import madx_parser
from sirepo.template.lattice import LatticeUtil
import copy
import csv
import os
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.madx
import socket

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_SUMMARY_CSV_FILE = 'summary.csv'
_PTC_TRACK_COLUMNS_FILE = 'ptc_track_columns.txt'
_PTC_TRACK_FILE = 'track.tfs'


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
            elementValues=_read_summary_line(run_dir),
            ptcTrackColumns=_get_ptc_track_columns(run_dir),
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        elementValues=_read_summary_line(
            run_dir,
            SCHEMA.constants.maxBPMPoints,
        ),
        ptcTrackColumns=_get_ptc_track_columns(run_dir),
    )


def _get_ptc_track_columns(run_dir):
    if run_dir.join(_PTC_TRACK_COLUMNS_FILE).exists():
        return pkio.read_text(_PTC_TRACK_COLUMNS_FILE).split(',')
    return []


def _get_target_info(info_all, target):
    for i in info_all:
        if i.name == target:
            return i, info_all.index(i)

    raise AssertionError(f'no target={target} in info_all={info_all}')


def sim_frame(frame_args):
    return _extract_report_elementAnimation(frame_args, frame_args.run_dir, _PTC_TRACK_FILE)


def _extract_report_elementAnimation(frame_args, run_dir, filename):
    data = frame_args.sim_in
    if sirepo.template.madx.is_parameter_report_file(filename):
        return sirepo.template.madx.extract_parameter_report(data, run_dir, filename)
    a = madx_parser.parse_tfs_page_info(run_dir.join(filename))
    d = data.models[frame_args.frameReport].id
    data.models[frame_args.frameReport] = frame_args
    n = frame_args.sim_in.models.externalLattice.models.elements[d].name
    i, x = _get_target_info(a, n)
    t = madx_parser.parse_tfs_file(run_dir.join(filename), want_page=x)
    return template_common.heatmap(
        [sirepo.template.madx.to_floats(t[frame_args.x]), sirepo.template.madx.to_floats(t[frame_args.y1])],
        frame_args,
        PKDict(
            x_label=sirepo.template.madx.field_label(frame_args.x),
            y_label=sirepo.template.madx.field_label(frame_args.y1),
            title='{}-{} at {}m, {}'.format(
                frame_args.x, frame_args.y1, i.s, i.name,
            ),
        ),
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
    madx = sirepo.simulation_db.read_json(
        _SIM_DATA.controls_madx_dir().join(
            data.simulationId,
            sirepo.simulation_db.SIMULATION_DATA_FILE,
        ),
    )
    _delete_unused_madx_models(madx)
    sirepo.template.madx.eval_code_var(madx)
    by_name = _delete_unused_madx_commands(madx)
    sirepo.template.madx.uniquify_elements(madx)
    _add_monitor(madx)
    madx.models.bunch.beamDefinition = 'gamma'
    _SIM_DATA.update_beam_gamma(by_name.beam)
    _SIM_DATA.init_currents(by_name.beam, madx.models)
    return _SIM_DATA.init_process_variables(PKDict(
        externalLattice=madx,
        optimizerSettings=_SIM_DATA.default_optimizer_settings(madx.models),
        command_beam=by_name.beam,
        command_twiss=by_name.twiss,
    ))


def stateless_compute_current_to_kick(data):
    return PKDict(
        kick=AmpConverter(data.command_beam, data.amp_table).current_to_kick(data.current),
    )


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

    if not by_name.twiss:
        by_name.twiss = PKDict(
            _id=LatticeUtil.max_id(data) + 2,
            _type='twiss',
            file='1',
        )
    by_name.twiss.sectorfile = '0'
    by_name.twiss.sectormap = '0'
    by_name.twiss.file = '1'
    data.models.commands = [
        by_name.beam,
        PKDict(
            _id=LatticeUtil.max_id(data) + 1,
            _type='select',
            flag='twiss',
            column='name,keyword,s,x,y',
        ),
        by_name.twiss,
    ]
    return by_name


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
    _generate_parameters(v, data)
    if data.models.controlSettings.operationMode == 'DeviceServer':
        _validate_process_variables(v, data)
    v.optimizerTargets = data.models.optimizerSettings.targets
    v.particleCount = data.models.externalLattice.models.bunch.numberOfParticles
    v.summaryCSV = _SUMMARY_CSV_FILE
    v.ptcTrackColumns = _PTC_TRACK_COLUMNS_FILE
    v.ptcTrackFile = _PTC_TRACK_FILE
    if data.get('report') == 'initialMonitorPositionsReport':
        v.optimizerSettings_method = 'runOnce'
    return res + template_common.render_jinja(SIM_TYPE, v)


def _generate_parameters(v, data):

    def _format_header(el_id, field):
        return f'el_{el_id}.{field}'

    v.ampTableNames = []
    v.ampTables = data.models.get('ampTables', PKDict())

    def _set_opt(el, field, all_correctors):
        count = len(all_correctors.corrector)
        all_correctors.corrector.append(el[_SIM_DATA.current_field(field)])
        el[field] = '{' + f'sr_opt{count}' + '}'
        all_correctors.header.append(_format_header(el._id, _SIM_DATA.current_field(field)))
        v.ampTableNames.append(el.ampTable if 'ampTable' in el else None)

    def _create_ptc_observes(instruments, data):
        for i, c in enumerate(data.models.commands):
            if c._type == 'ptc_create_universe':
                # POSIT: assume if ptc_create_universe exits, all other commands are there too
                break
        else:
            raise AssertionError(f'adding only ptc_observes but no ptc_create_universe found commands={data.models.commands}')
        data.models.commands[i + 1:i + 1] = _set_ptc_ids(
            [
                PKDict(
                    _type='ptc_observe',
                    place=o.name,
                ) for o in instruments
            ],
            data,
        )

    def _set_ptc_ids(ptc_commands, data):
        m = LatticeUtil.max_id(data) + 1
        for i,  c in enumerate(ptc_commands):
            c._id = m + i
        return ptc_commands

    def _gen_full_ptc(instruments, data):
        data.models.commands.extend(_set_ptc_ids(
            [
                PKDict(_type='ptc_create_universe'),
                PKDict(_type='ptc_create_layout'),
                PKDict(_type='ptc_track', file='1'),
                PKDict(_type='ptc_track_end'),
                PKDict(_type='ptc_end'),
            ],
            data,
        ))
        _create_ptc_observes(instruments, data)

    def _add_ptc(instruments, data):
        u = LatticeUtil.find_first_command(data, 'ptc_create_universe')
        if not u:
            _gen_full_ptc(instruments, data)
            return
        _create_ptc_observes(instruments, data)

    c = PKDict(
        header=[],
        corrector=[],
    )
    i = []
    madx = data.models.externalLattice.models
    k = data.models.optimizerSettings.inputs.kickers
    q = data.models.optimizerSettings.inputs.quads
    header = []
    for el in _SIM_DATA.beamline_elements(madx):
        if el.type == 'KICKER' and k[str(el._id)]:
            _set_opt(el, 'hkick', c)
            _set_opt(el, 'vkick', c)
        elif el.type == 'INSTRUMENT':
            i.append(el)
        elif el.type in ('HKICKER', 'VKICKER') and k[str(el._id)]:
            _set_opt(el, 'kick', c)
        elif el.type == 'QUADRUPOLE' and q[str(el._id)]:
            _set_opt(el, 'k1', c)
        elif el.type == 'MONITOR':
            header += [_format_header(el._id, x) for x in ('x', 'y')]
        elif el.type == 'HMONITOR':
            header += [_format_header(el._id, 'x')]
        elif el.type == 'VMONITOR':
            header += [_format_header(el._id, 'y')]
    v.summaryCSVHeader = ','.join(c.header + header)
    v.initialCorrectors = '[{}]'.format(','.join([str(x) for x in c.corrector]))
    v.correctorCount = len(c.corrector)
    v.monitorCount = len(header) / 2
    if i:
        _add_ptc(i, data.models.externalLattice)
    if data.models.controlSettings.operationMode == 'madx':
        data.models.externalLattice.report = ''
        v.madxSource = sirepo.template.madx.generate_parameters_file(data.models.externalLattice)


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


def _validate_process_variables(v, data):
    settings = data.models.controlSettings
    if not settings.deviceServerURL:
        raise AssertionError('Missing DeviceServer URL value')
    elmap = PKDict({e._id: e for e in data.models.externalLattice.models.elements})
    properties = PKDict(
        read=[],
        write=[],
    )
    for pv in settings.processVariables:
        el = elmap[pv.elId]
        name = el.name
        if not pv.pvName:
            raise AssertionError(f'Missing Process Variable Name for beamline element {name}')
        values = re.split(r':', pv.pvName)
        if len(values) != 2:
            raise AssertionError(f'Beamline element {name} Process Variable must contain one : separator')
        idx = None
        if pv.isWritable == '0':
            m = re.search(r'\[(\d+)\]', values[1])
            if m:
                idx = int(m.group(1))
                values[1] = re.sub(r'\[.*$', '', values[1])
        properties['write' if pv.isWritable == '1' else 'read'].append(PKDict(
            device=values[0],
            name=values[1],
            index=idx,
            type=el.type,
        ))
    v.properties = properties
    v.property_types = properties.keys()
    config = PKDict(
        #TODO(pjm): set from config
        user='moeller',
        procName='RadiaSoft/Sirepo',
        procId=os.getpid(),
        machine=socket.gethostname(),
    )
    v.deviceServerSetContext = '&'.join([
        f'{k}={config[k]}' for k in config
    ])
