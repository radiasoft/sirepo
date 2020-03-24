# -*- coding: utf-8 -*-
u"""MAD-X parser.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template.line_parser import LineParser
import re
import sirepo.sim_data

_SIM_DATA = sirepo.sim_data.get_class('madx')
_SCHEMA = _SIM_DATA.schema()

_IGNORE_COMMANDS = set([
    'aperture', 'assign', 'beta0', 'coguess', 'constraint',
    'correct', 'create', 'ealign', 'efcomp', 'emit', 'endedit',
    'endmatch', 'eoption', 'esave', 'exec', 'fill', 'global',
    'install', 'jacobian', 'lmdif', 'lmdif', 'makethin', 'match',
    'observe', 'option', 'plot', 'print', 'readtable', 'reflect',
    'return', 'run', 'save', 'savebeta', 'select',
    'select_ptc_normal', 'seqedit', 'set', 'setplot', 'setvars',
    'setvars_lin', 'show', 'simplex', 'sixtrack', 'sodd', 'start',
    'stop', 'survey', 'sxfread', 'sxfwrite', 'system', 'touschek',
    'twiss', 'use_macro', 'usekick', 'usemonitor', 'value',
    'vary', 'weight', 'wire', 'write',
])

#TODO(pjm): convert to a python class, state -> self

def parse_file(lattice_text):
    data = simulation_db.default_data(_SIM_DATA.sim_type())
    data.models.rpnVariables = {}
    data.models.sequences = []
    state = PKDict(
        #TODO(pjm): use parser line number for assertion errors
        parser=LineParser(),
        # None | sequence | track | match | edit
        container=None,
        models=data.models,
        elements_by_name=PKDict(),
    )
    lines = lattice_text.replace('\r', '').split('\n')
    _parse_lines(state, lines)
    _code_variables_to_lowercase(state)
    _convert_sequences_to_beamlines(state)
    _set_default_beamline(state)
    return data


def _code_variables_to_lowercase(state):
    from sirepo.template import madx
    cv = madx.madx_code_var(state.models.rpnVariables)
    for el in state.models.elements:
        for f in _SCHEMA.model[el.type]:
            if _SCHEMA.model[el.type][f][1] == 'RPNValue':
                if cv.is_var_value(el[f]):
                    el[f] = el[f].lower()


def _convert_sequences_to_beamlines(state):
    from sirepo.template import madx, lattice
    cv = madx.madx_code_var(state.models.rpnVariables)
    data = PKDict(
        models=state.models,
    )
    drifts = PKDict()
    for el in data.models.elements:
        if el.type == 'DRIFT':
            length = _format_length(_eval_var(cv, el.l))
            if length not in drifts:
                drifts[length] = el._id
    util = lattice.LatticeUtil(data, _SCHEMA);
    for seq in data.models.sequences:
        beamline = PKDict(
            name=seq.name,
            items=[],
        )
        #TODO(pjm): need to realign elements which are not "at" entry
        # assert 'refer' not in seq or seq.refer.lower() == 'entry', \
        #     'unsupported sequence refer: {}: {}'.format(seq.name, seq.refer)
        prev = None
        for item in seq['items']:
            el = util.id_map[item[0]]
            at = _eval_var(cv, item[1])
            if prev is not None:
                d = _get_drift(state, drifts, at - prev)
                if d:
                    beamline['items'].append(d._id)
            beamline['items'].append(el._id)
            prev = at + _eval_var(cv, el.get('l', 0))
        if len(beamline['items']):
            if 'l' in seq:
                d = _get_drift(state, drifts, _eval_var(cv, seq.l) - prev)
                if d:
                    beamline['items'].append(d._id)
            beamline.id = state.parser.next_id()
            data.models.beamlines.append(beamline)
    del data.models['sequences']
    util.sort_elements_and_beamlines()


def _eval_var(code_var, value):
    (v, err) = code_var.eval_var(value)
    assert not err, err
    return float(v)


def _format_length(length):
    res = '{:.8E}'.format(length)
    res = re.sub(r'(\.\d+?)(0+)E', r'\1e', res)
    res = re.sub(r'e\+00$', '', res)
    return res


def _get_drift(state, drifts, length):
    if length <= 0:
        if length < 0:
            pkdlog('warning: negative drift: {}', length)
        return None
    length = _format_length(length)
    if length not in drifts:
        drift = PKDict(
            _id=state.parser.next_id(),
            l=length,
            name='D{}'.format(length),
            type='DRIFT',
        )
        state.models.elements.append(drift)
        drifts[length] = drift
    return drifts[length]


def _parse_beamline(state, label, values):
    #pkdp('beamline: {}', values)
    assert label
    values[-1] = re.sub('\s*\)$', '', values[-1])
    values[0] = re.sub('^.*?=\s*\(\s*', '', values[0])
    res = PKDict(
        name=label,
        id=state.parser.next_id(),
        items=[],
    )
    for v in values:
        count = 1
        m = re.match(r'^(\d+)\s*\*\s*([\w.]+)$', v)
        if m:
            count = int(m.group(1))
            v = m.group(2)
        reverse = False
        if v[0] == '-':
            reverse = True
            v = v[1:]
        el = state.elements_by_name[v.upper()]
        assert el, 'line: {} element not found: {}'.format(label, v)
        el_id = el._id if '_id' in el else el.id
        for _ in range(count):
            res['items'].append(-el_id if reverse else el_id)
    assert label.upper() not in state.elements_by_name
    #pkdp('adding beamline: {}', label.upper())
    state.elements_by_name[label.upper()] = res
    state.models.beamlines.append(res)


def _parse_element(state, cmd, label, values):
    res = _parse_fields(values, PKDict(
        name=label,
        _id=state.parser.next_id(),
    ))
    res.type = cmd
    if state.container:
        assert 'at' in res, 'sequence element missing "at": {}'.format(values)
        at = res.at
        del res['at']
        if cmd not in _SCHEMA.model:
            parent = state.elements_by_name[cmd]
            assert parent
            assert len(res) >= 3
            if len(res) == 3:
                state.container['items'].append([parent._id, at])
                return
        assert label, 'unlabeled element: {}'.format(values)
        state.container['items'].append([res._id, at])
    assert 'at' not in res
    # copy in superclass values
    while cmd not in _SCHEMA.model:
        parent = state.elements_by_name[cmd]
        assert parent and parent.type
        res = PKDict(parent.items() + res.items())
        res.type = parent.type
        cmd = parent.type
    _SIM_DATA.update_model_defaults(res, res.type)
    state.models.elements.append(res)
    if not label:
        label = values[0].upper()
        assert label in state.elements_by_name, 'no element for label: {}: {}'.format(label, values)
        state.elements_by_name[label].update(res)
    elif label.upper() in state.elements_by_name:
        pkdlog('duplicate label: {}', values)
    else:
        state.elements_by_name[label.upper()] = res
    #pkdp('el: {}: {}', res.name, res.type)
    return res


def _parse_fields(values, res):
    #TODO(pjm): only add fields which are in the schema
    for value in values[1:]:
        #pkdp('  field: {}', value)
        m = re.match(r'^\s*([\w.]+)\s*:?=\s*(.+?)\s*$', value)
        if m:
            f, v = m.group(1, 2)
            assert f not in res, 'field already defined: {}, values: {}'.format(f, values)
            res[f.lower()] = v
            continue
        m = re.match(r'^\s*(!)?\s*([\w.]+)\s*$', value)
        assert m, 'failed to parse field assignment: {}'.format(value)
        v, f = m.group(1, 2)
        res[f.lower()] = '0' if v else '1'
    return res


def _parse_lines(state, lines):
    prev_line = ''
    in_comment = False
    for line in lines:
        state.parser.increment_line_number()
        line = re.sub(r'\&\s*$', '', line)
        # strip comments
        line = line.strip()
        line = re.sub(r'(.*?)(!|//).*$', r'\1', line)
        line = re.sub(r'\/\*.*?\*\/', '', line)
        # special case, some commands often missing a comma
        line = re.sub(r'^\s*(title|exec|call)\s+([^,])', r'\1, \2', line, flags=re.IGNORECASE)
        if in_comment and re.search(r'^.*\*\/', line):
            line = re.sub(r'^.*\*\/', '', line)
            in_comment = False
        if re.search(r'\/\*.*$', line):
            line = re.sub(r'\/\*.*$', '', line)
            in_comment = True
        if not line or in_comment:
            continue
        while ';' in line:
            m = re.match(r'^(.*?);(.*)$', line)
            assert m, 'parse ; failed: {}'.format(line)
            item = (prev_line + ' ' + m.group(1)).strip()
            _parse_values(state, _split_values(item))
            line = m.group(2)
            prev_line = ''
        prev_line += line
    state.models['rpnVariables'] = [
        PKDict(name=k.lower(), value=v.lower()) for k, v in state.models.rpnVariables.items()
    ]


def _parse_statement(state, cmd, label, values):
    #pkdp('cmd: {}, label: {}, values: {}', cmd, label, values)
    if cmd.upper() in _SCHEMA.model or cmd.upper() in state.elements_by_name:
        _parse_element(state, cmd.upper(), label, values)
        return
    cmd = cmd.lower()
    if state.container and cmd == 'end{}'.format(state.container.type):
        assert len(values) == 1, 'invalid end{}: {}'.format(state.container, values)
        state.container = None
        return
    if cmd  in ('sequence', 'track'):
        state.container = PKDict(
            name=label,
            type=cmd,
            _id=state.parser.next_id(),
        )
        _parse_fields(values, state.container)
        state.container['items'] = []
        if cmd == 'sequence':
            state.models.sequences.append(state.container)
    elif 'command_{}'.format(cmd) in _SCHEMA.model:
        cmd = 'command_{}'.format(cmd)
        res = PKDict(
            _type=cmd,
            _id=state.parser.next_id(),
        )
        _parse_fields(values, res)
        state.models.commands.append(res)
        #pkdp('cmd: {}', res._type)
    elif cmd == 'line':
        _parse_beamline(state, label, values)
    elif cmd == 'title':
        if len(values) > 1:
            state.models.simulation.name = values[1][1:-1]
    elif cmd not in _IGNORE_COMMANDS:
        assert cmd != 'call', '"CALL" statement not supported, combine subfiles into one input file before import'
        if re.search(r'^ptc_', cmd):
            pass
        else:
            pkdlog('unknown cmd: {}', values)
    return state


def _parse_values(state, values):
    #pkdp('parse values: {}', values)
    assert len(values)
    if len(values) == 1 and '=' in values[0] and not re.search(r'\Wline\s*=s*\(', values[0].lower()):
        # a variable assignment
        m = re.match(r'.*?([\w.\']+)\s*:?=\s*(.*)$', values[0])
        assert m, 'invalid variable assignment: {}'.format(values)
        name = m.group(1)
        v = m.group(2)
        if name not in state.models.rpnVariables:
            state.models.rpnVariables[name] = v
        return
    if ':' in values[0]:
        m = re.match(r'([\w.]+)\s*:\s*([\w.]+)', values[0])
        assert m, 'label match failed: {}'.format(values[0])
        label, cmd = m.group(1, 2)
    else:
        label, cmd = None, values[0]
    return _parse_statement(state, cmd, label, values)


def _set_default_beamline(state):
    name = None
    for cmd in state.models.commands:
        if cmd._type == 'command_use':
            name = cmd.get('sequence', cmd.get('period', None))
            if name and name.upper() in state.elements_by_name:
                name = name.upper()
                break
            name = None
    beamline_id = None
    if name:
        beamline_id = state.elements_by_name[name].id
    elif len(state.models.beamlines):
        beamline_id = state.models.beamlines[-1].id
    state.models.simulation.visualizationBeamlineId = beamline_id


def _split_values(item):
    #pkdp('item: {}', item)
    # split items into values by commas
    values = []
    while item and len(item):
        item = item.strip()
        #pkdp('match item: {}', item)
        m = re.match(r'^\s*((?:[\w.\']+\s*:?=\s*)?(?:(?:".*?")|(?:\'.*?\')|(?:\{.*?\})|(?:\w+\(.*?\))))(?:,(.*))?$', item)
        if m:
            values.append(m.group(1))
            assert item != m.group(2)
            item = m.group(2)
            continue
        m = re.match(r'^\s*(.+?)(?:,(.*))?$', item)
        if m:
            values.append(m.group(1).strip())
            assert item != m.group(2)
            item = m.group(2)
            continue
        assert False, 'line parse failed: {}'.format(item)
    return values
