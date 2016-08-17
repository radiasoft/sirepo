# -*- coding: utf-8 -*-
u"""elegant lattice parser.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import re

def parse_file(lattice_text):
    lines = lattice_text.split('\n')
    prev_line = ''
    state = {
        'models': {
            'beamlines': [],
            'elements': [],
            'default_beamline_name': None,
        },
        'rpnVariables': {},
        'line_number': 0,
        'id': 0,
    }
    for line in lines:
        state['line_number'] += 1
        if re.search(r'^\!', line):
            continue
        if re.search(r'\&\s*$', line):
            prev_line += re.sub(r'(\s*\&\s*)$', '', line)
            continue
        if not _parse_line(prev_line + line, state):
            break
        prev_line = ''
    state['models']['rpnVariables'] = map(lambda x: { 'name': x, 'value': state['rpnVariables'][x] }, state['rpnVariables'].keys())
    return state['models']


def _assert_char(state, char):
    if _next_char(state) != char:
        _raise_error(state, 'expected {}'.format(char))
    _ignore_whitespace(state)


def _assert_end_of_line(state):
    _ignore_whitespace(state)
    if _has_char(state) and _peek_char(state) != '!':
        _raise_error(state, 'left-over input')


def _has_char(state):
    return state['index'] < len(state['line'])


def _ignore_whitespace(state):
    while _has_char(state) and re.search(r'\s', _peek_char(state)):
        _next_char(state)


def _next_char(state):
    if _has_char(state):
        c = state['line'][state['index']]
        state['index'] += 1
        return c
    return None


def _next_id(state):
    state['id'] += 1
    return state['id']


def _parse_beamline(name, state):
    _assert_char(state, '=')
    state['models']['beamlines'].append({
        'name': name,
        'id': _next_id(state),
        'items': _parse_beamline_items(state),
    })


def _parse_beamline_items(state):
    _assert_char(state, '(')
    items = []
    while True:
        value = _parse_value(state)
        if not value:
            if _peek_char(state) == ',':
                _assert_char(state, ',')
                continue
            _raise_error(state, 'expecting beamline element')
        if re.search(r'[0-9]', value[0]):
            repeat_count = int(value)
            _assert_char(state, '*')
            if _peek_char(state) == '(':
                repeat_items = _parse_beamline_items(state)
            else:
                repeat_items = [_parse_value(state)]
            for _ in range(repeat_count):
                for item in repeat_items:
                    items.append(item)
        else:
            items.append(value)

        if _peek_char(state) == ',':
            _assert_char(state, ',')
        else:
            break
    _assert_char(state, ')')
    return items


def _parse_element(name, type, state):
    el = {
        '_id': _next_id(state),
        'type': type,
        'name': name,
    }
    state['models']['elements'].append(el)
    while _peek_char(state) == ',':
        _assert_char(state, ',')
        field = _parse_value(state)
        if not field:
            _assert_end_of_line(state)
        if _peek_char(state) == '=':
            _assert_char(state, '=')
            el[field.lower()] = _parse_value(state)


def _parse_line(line, state):
    state['line'] = line
    state['index'] = 0
    name = _parse_value(state, r'[:\s,=)*]')
    if name == '%':
        # rpn value
        line = re.sub(r'\s*%\s*', '', line)
        _save_rpn_variables(line, state['rpnVariables'])
        return True
    if not name or not re.search(r'[A-Z]', name[0], re.IGNORECASE):
        if name and name.upper() == '#INCLUDE':
            _raise_error(state, '#INCLUDE files not supported')
        return True
    if _peek_char(state) != ':':
        if name.upper() == 'USE' and _peek_char(state) == ',':
            _assert_char(state, ',')
            state['models']['default_beamline_name'] = _parse_value(state)
            return True
        if name.upper() == 'RETURN':
            return False
        # ignore non-definition lines
        return True
    _assert_char(state, ':')
    type = _parse_value(state)
    if not type:
        _raise_error(state, 'expected type')
    if type.upper() == 'LINE':
        _parse_beamline(name, state)
    else:
        _parse_element(name, type, state)
    _assert_end_of_line(state)
    return True


def _parse_quoted_value(state):
    _assert_char(state, '"')
    value = _read_until(state, '"')
    if value is not None:
        _assert_char(state, '"')
    return value


def _parse_value(state, end_regex=None):
    if _peek_char(state) == '"':
        return _parse_quoted_value(state)
    return _read_until(state, end_regex if end_regex else r'[\s,=\!)*]')


def _peek_char(state):
    if _has_char(state):
        return state['line'][state['index']]
    return None


def _raise_error(state, message):
    raise IOError('line {}, {}: {}'.format(state['line_number'], message, state['line'][state['index']:]))


def _read_until(state, regex):
    # Reads until the end-of-line or the character regex is matched
    value = ''
    while _has_char(state) and not re.search(regex, _peek_char(state)):
        value += _next_char(state)
    _ignore_whitespace(state)
    return value


def _save_rpn_variables(line, rpn_variables):
    m = re.match(r'(.*) sto ((\S+).*)', line)
    if m:
        val = _save_rpn_variables(m.group(1), rpn_variables)
        var = m.group(3)
        rpn_variables[var] = val
        return m.group(2)
    return line
