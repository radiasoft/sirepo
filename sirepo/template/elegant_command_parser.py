# -*- coding: utf-8 -*-
u"""elegant command parser.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import re

from sirepo.template.line_parser import LineParser

def parse_file(command_text):
    parser = LineParser(0)
    lines = command_text.replace('\r', '').split('\n')
    prev_line = ''
    commands = []

    for line in lines:
        parser.increment_line_number()
        if re.search(r'^#', line):
            continue
        line = re.sub(r'\!.*$', '', line)
        if not line:
            continue
        if re.search(r'\&end', line):
            if not _parse_line(parser, prev_line + ' ' + line, commands):
                break
            prev_line = ''
        else:
            prev_line += ' ' + line
    if prev_line and re.search(r'\&', prev_line):
        parser.raise_error('missing &end for command: {}'.format(prev_line))
    return {
        'models': {
            'commands': commands,
        }
    }


def _parse_array_value(parser):
    # read off the end of the array value list
    # parse values until a "&end" or "value =" is reached
    #
    # response[2] = %s.vhrm, %s.hvrm,
    # distribution_type[0] = "gaussian", "gaussian",
    # enforce_rms_values[0] = 1,1,1,
    # distribution_type[0] = gaussian, gaussian, hard-edge,
    # distribution_type[0] = 3*"gaussian",
    # distribution_cutoff[0] = 3*3,
    res = ''
    index = parser.get_index()
    while True:
        value = parser.parse_value()
        if value == '&end':
            parser.reset_index(index)
            break
        parser.ignore_whitespace()
        if parser.peek_char() == '=':
            parser.reset_index(index)
            break
        if value:
            res += value
        else:
            if parser.peek_char() == ',':
                parser.assert_char(',')
                res += ','
            elif parser.peek_char() == '*':
                parser.assert_char('*')
                res += '*'
            else:
                parser.raise_error('expecting an array value')
        index = parser.get_index()
    if not res:
        parser.raise_error('missing array value')
    res = re.sub(r',$', '', res)
    return res


def _parse_line(parser, line, commands):
    parser.set_line(line)
    parser.ignore_whitespace()
    parser.assert_char('&')
    command = {
        '_id': parser.next_id(),
        '_type': parser.parse_value(r'\s+'),
    }
    if command['_type'] == 'stop':
        return False
    parser.ignore_whitespace()
    while True:
        value = parser.parse_value()
        if not value:
            if parser.peek_char() == ',':
                parser.assert_char(',')
                continue
            parser.raise_error('expecting a command element')
        if value == '&end':
            break
        if parser.peek_char() == '=':
            parser.assert_char('=')
            if re.search(r'\[', value):
                command[value.lower()] = _parse_array_value(parser)
            else:
                command[value.lower()] = parser.parse_value(r'[\s,=\!)]')
        else:
            parser.raise_error('trailing input: {}'.format(value))
    parser.assert_end_of_line()
    commands.append(command)
    return True
