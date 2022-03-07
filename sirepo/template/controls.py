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
        e = _read_summary_line(run_dir)
        return PKDict(
            percentComplete=0,
            frameCount=1 if e else 0,
            elementValues=e,
            ptcTrackColumns=_get_ptc_track_columns(run_dir),
            twissColumns=sirepo.template.madx.PTC_OBSERVE_TWISS_COLS,
        )
    e = _read_summary_line(
        run_dir,
        SCHEMA.constants.maxBPMPoints,
    )
    return PKDict(
        percentComplete=100,
        frameCount=1 if e else 0,
        elementValues=e,
        ptcTrackColumns=_get_ptc_track_columns(run_dir),
        twissColumns=sirepo.template.madx.PTC_OBSERVE_TWISS_COLS,
    )


def _get_ptc_track_columns(run_dir):
    if run_dir.join(_PTC_TRACK_COLUMNS_FILE).exists():
        return pkio.read_text(_PTC_TRACK_COLUMNS_FILE).split(',')
    return []


def _get_target_info(info_all, frame_args):
    data = frame_args.sim_in
    idx = data.models[frame_args.frameReport].id
    #idx = frame_args.sim_in.models[frame_args.frameReport].id
    elements = frame_args.sim_in.models.externalLattice.models.elements
    target = -1
    for i in range(len(elements)):
        if elements[i].type == 'INSTRUMENT':
            target += 1
        if idx == i:
            break
    # n = frame_args.sim_in.models.externalLattice.models.elements[
    #     data.models[frame_args.frameReport].id].name
    # for i, o in enumerate(info_all):
    #     if o.name == target.upper():
    #         return o, i
    if target < 0:
        raise AssertionError(f'no target={elements[idx]} in info_all={info_all}')
    count = -1
    target_rec = None
    for rec in info_all:
        if re.search(r'MARKER\d+_INSTRUMENT', rec.name):
            count += 1
            if count == target:
                target_rec = rec
                break;
    target_rec.name = elements[idx].name
    return target_rec, count


def sim_frame(frame_args):
    return _extract_report_elementAnimation(frame_args, frame_args.run_dir, _PTC_TRACK_FILE)


def _extract_report_elementAnimation(frame_args, run_dir, filename):
    data = frame_args.sim_in
    if frame_args.frameReport == 'instrumentAnimationTwiss':
        data.report = frame_args.frameReport
        data.models[data.report] = frame_args
        return sirepo.template.madx.extract_report_twissFromParticlesAnimation(data, run_dir, _PTC_TRACK_FILE)
    a = madx_parser.parse_tfs_page_info(run_dir.join(filename))
    frame_args.plotRangeType = 'fixed'
    frame_args.verticalSize = frame_args.particlePlotSize
    frame_args.verticalOffset = 0
    frame_args.horizontalSize = frame_args.particlePlotSize
    frame_args.horizontalOffset = 0
    i, x = _get_target_info(a, frame_args)
    t = madx_parser.parse_tfs_file(run_dir.join(filename), want_page=x)
    data.models[frame_args.frameReport] = frame_args
    return template_common.heatmap(
        [sirepo.template.madx.to_floats(t[frame_args.x]), sirepo.template.madx.to_floats(t[frame_args.y1])],
        frame_args,
        PKDict(
            x_label=sirepo.template.madx.field_label(frame_args.x),
            y_label=sirepo.template.madx.field_label(frame_args.y1),
            title='{}-{} at {:.3f}m, {}'.format(
                frame_args.x, frame_args.y1, float(i.s), i.name,
            ),
            global_min=0,
            global_max=2,
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
    beam = _delete_unused_madx_commands(madx)
    sirepo.template.madx.uniquify_elements(madx)
    _add_monitor(madx)
    madx.models.simulation.computeTwissFromParticles = '1'
    _SIM_DATA.update_beam_gamma(beam)
    madx.models.bunch.beamDefinition = 'gamma'
    _SIM_DATA.init_currents(beam, madx.models)
    _SIM_DATA.add_ptc_track_commands(madx)
    return _SIM_DATA.init_process_variables(PKDict(
        externalLattice=madx,
        optimizerSettings=_SIM_DATA.default_optimizer_settings(madx.models),
        command_beam=beam,
        bunch=madx.models.bunch,
    ))


def stateless_compute_current_to_kick(data):
    return PKDict(
        kick=AmpConverter(data.command_beam, data.amp_table).current_to_kick(data.current),
    )


def stateless_compute_kick_to_current(data):
    return PKDict(
        current=AmpConverter(data.command_beam, data.amp_table).kick_to_current(data.kick),
    )


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _add_monitor(data):
    for i, e in enumerate(data.models.elements):
        if e.type == 'MARKER':
            data.models.elements[i] = PKDict(
                _id=e._id,
                name=e.name,
                type='MONITOR',
            )
    if not list(filter(lambda el: el.type == 'MONITOR', data.models.elements)):
        m = PKDict(
            _id=LatticeUtil.max_id(data) + 1,
            name='M1',
            type='MONITOR',
        )
        data.models.elements.append(m)
        assert len(data.models.beamlines) == 1, \
            f'expecting 1 beamline={data.models.beamlines}'
        data.models.beamlines[0]['items'].append(m._id)


def _delete_unused_madx_commands(data):
    # remove all commands except first beam
    beam = None
    for c in data.models.commands:
        if c._type == 'beam':
            beam = c
            _SIM_DATA.update_model_defaults(c, 'command_beam')
            break
    data.models.commands = [
        PKDict(
            _type='option',
            _id=LatticeUtil.max_id(data),
            echo='0',
        ),
        beam,
    ]
    return beam


def _delete_unused_madx_models(data):
    for m in list(data.models.keys()):
        if m not in [
            'beamlines',
            'commands',
            'elements',
            'report',
            'rpnVariables',
            'simulation',
            'bunch',
        ]:
            data.models.pkdel(m)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    _generate_parameters(v, data)
    if data.models.controlSettings.operationMode == 'DeviceServer':
        _validate_process_variables(v, data)
    else:
        sirepo.template.madx._add_marker_and_observe(data.models.externalLattice)
    v.optimizerTargets = data.models.optimizerSettings.targets
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

    c = PKDict(
        header=[],
        corrector=[],
    )
    madx = data.models.externalLattice.models
    k = data.models.optimizerSettings.inputs.kickers
    q = data.models.optimizerSettings.inputs.quads
    header = []
    for el in _SIM_DATA.beamline_elements(madx):
        if el.type == 'KICKER' and k[str(el._id)]:
            _set_opt(el, 'hkick', c)
            _set_opt(el, 'vkick', c)
        # elif el.type == 'INSTRUMENT':
        #     i.append(el)
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
    v.summaryCSVHeader = ','.join(c.header + header + ['cost'])
    v.initialCorrectors = '[{}]'.format(','.join([str(x) for x in c.corrector]))
    v.correctorCount = len(c.corrector)
    v.monitorCount = len(header)
    v.mc2 = SCHEMA.constants.particleMassAndCharge.proton[0]
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
        user='pmoeller',
        procName='RadiaSoft/Sirepo',
        procId=os.getpid(),
        machine=socket.gethostname(),
    )
    v.deviceServerSetContext = '&'.join([
        f'{k}={config[k]}' for k in config
    ])
