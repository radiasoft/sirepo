# -*- coding: utf-8 -*-
u"""elegant lattice parser.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import re

from sirepo.template.line_parser import LineParser

# a map of old elegant names to the new name
_FIELD_ALIAS = {
    'bmax': 'b_max',
}


def parse_file(lattice_text, maxId=0):
    parser = LineParser(maxId)
    lines = lattice_text.replace('\r', '').split('\n')
    prev_line = ''
    models = {
        'beamlines': [],
        'elements': [],
        'default_beamline_name': None,
        'rpnVariables': {},
    }
    for line in lines:
        parser.increment_line_number()
        if re.search(r'^\s*\!', line):
            continue
        if re.search(r'\&\s*$', line):
            prev_line += re.sub(r'(\s*\&\s*)$', '', line)
            continue
        if not _parse_line(parser, prev_line + line, models):
            break
        prev_line = ''
    models['rpnVariables'] = map(lambda x: { 'name': x, 'value': models['rpnVariables'][x] }, models['rpnVariables'].keys())
    return models


def _parse_beamline(parser, name):
    parser.assert_char('=')
    return {
        'name': name,
        'id': parser.next_id(),
        'items': _parse_beamline_items(parser),
    }


def _parse_beamline_items(parser):
    parser.assert_char('(')
    items = []
    while True:
        value = parser.parse_value()
        if not value:
            if parser.peek_char() == ',':
                parser.assert_char(',')
                continue
            parser.raise_error('expecting beamline element')
        if re.search(r'^[0-9]+$', value):
            repeat_count = int(value)
            parser.assert_char('*')
            if parser.peek_char() == '(':
                repeat_items = _parse_beamline_items(parser)
            else:
                repeat_items = [parser.parse_value()]
            for _ in range(repeat_count):
                for item in repeat_items:
                    items.append(item)
        else:
            items.append(value)

        if parser.peek_char() == ',':
            parser.assert_char(',')
        else:
            break
    parser.assert_char(')')
    return items


def _parse_element(parser, name, type):
    el = {
        '_id': parser.next_id(),
        'type': type,
        'name': name,
    }
    while parser.peek_char() == ',':
        parser.assert_char(',')
        field = parser.parse_value()
        if not field:
            parser.assert_end_of_line()
        if parser.peek_char() == '=':
            parser.assert_char('=')
            f = field.lower()
            if f in _FIELD_ALIAS:
                f = _FIELD_ALIAS[f]
            el[f] = parser.parse_value()
    # ignore end of line ';'
    if parser.peek_char() == ';':
        parser.assert_char(';')
    return el


def _parse_line(parser, line, models):
    line = line.lstrip()
    parser.set_line(line)
    name = parser.parse_value(r'[:\s,=)*]')
    if re.search(r'^\%', name):
        # rpn value
        line = re.sub(r'\s*%\s*', '', line)
        line = re.sub(r'\s+', ' ', line)
        _save_rpn_variables(line, models['rpnVariables'])
        return True
    if not name or not re.search(r'[0-9A-Z]', name[0], re.IGNORECASE):
        if name and name.upper() == '#INCLUDE':
            parser.raise_error('#INCLUDE files not supported')
        return True
    if parser.peek_char() != ':':
        if name.upper() == 'USE' and parser.peek_char() == ',':
            parser.assert_char(',')
            models['default_beamline_name'] = parser.parse_value()
            return True
        if name.upper() == 'RETURN':
            return False
        # ignore non-definition lines
        return True
    parser.assert_char(':')
    type = parser.parse_value()
    if not type:
        parser.raise_error('expected type')
    if type.upper() == 'LINE':
        models['beamlines'].append(_parse_beamline(parser, name))
    else:
        models['elements'].append(_parse_element(parser, name, type))
    parser.assert_end_of_line()
    return True


def _save_rpn_variables(line, rpn_variables):
    m = re.match(r'(.*) sto ((\S+).*)', line)
    if m:
        val = _save_rpn_variables(m.group(1), rpn_variables)
        var = m.group(3)
        rpn_variables[var] = val
        return m.group(2)
    return line
