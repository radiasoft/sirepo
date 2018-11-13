# -*- coding: utf-8 -*-
u"""zgoubi input file parser.

l:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template.line_parser import LineParser
import re

_COMMAND_INDEX_POS = 110


def parse_file(zgoubi_text, max_id=0):
    parser = LineParser(max_id)
    lines = zgoubi_text.replace('\r', '').split('\n')
    elements = []
    # skip first documentation line
    title = lines.pop(0)
    parser.increment_line_number()
    current_command = None
    for line in lines:
        parser.increment_line_number()
        line = re.sub(r'\!.*$', '', line)
        line = re.sub(r'^\s+', '', line)
        line = re.sub(r'\s+$', '', line)
        if not line:
            continue
        keyword = _parse_keyword(line)
        if keyword:
            if current_command:
                _add_command(parser, current_command, elements)
            if keyword == 'END':
                current_command = None
                break
            line = _strip_command_index(line)
            current_command = [line.split()]
            current_command[0][0] = keyword
        else:
            line = line.lstrip()
            current_command.append(line.split())
    assert current_command is None, 'missing END element'
    return title, elements


def _add_command(parser, command, elements):
    command_type = command[0][0]
    method = '_zgoubi_{}'.format(command_type).lower()
    if method not in globals():
        pkdlog('unknown zgoubi element: {}', method)
        return
    el = globals()[method](command)
    if el:
        elements.append(el)


def _parse_command(command, command_def):
    res = _parse_command_header(command)
    for i in range(len(command_def)):
        _parse_command_line(res, command[i + 1], command_def[i])
    return res


def _parse_command_header(command):
    return _parse_command_line(pkcollections.Dict({}), command[0], 'type *name *label2')


def _parse_command_line(element, line, line_def):
    for k in line_def.split(' '):
        if k[0] == '*':
            k = k[1:]
            if not len(line):
                break;
        element[k] = line.pop(0)
    return element


def _parse_keyword(line):
    m = re.match(r"\s*'(\w+)'", line)
    if m:
        return m.group(1).upper()
    return None


def _strip_command_index(line):
    # strip the command index if present
    if len(line) >= _COMMAND_INDEX_POS:
        line = re.sub(r'\s+\d+\s*$', '', line)
    return line


def _zgoubi_autoref(command):
    i = command[1][0]
    assert i == '4', '{}: only AUTOREF 4 is supported for now'.format(i)
    return _parse_command(command, [
        'I',
        'XCE YCE ALE',
    ])

def _zgoubi_bend(command):
    res = _parse_command(command, [
        'IL',
        'l Sk B1',
        'X_E LAM_E W_E',
        'NCE C_0 C_1 C_2 C_3 C_4 C_5',
        'X_S LAM_S W_S',
        'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5',
        'XPAS',
        'KPOS XCE YCE ALE',
    ])
    assert res['KPOS'] in ('1', '2', '3'), '{}: BEND KPOS not yet supported'.format(res['KPOS'])
    return res

def _zgoubi_cavite(command):
    i = command[1][0]
    if i == '1':
        return _parse_command(command, [
            'IOPT',
            'L h',
            'V',
        ])
    if i == '2':
        return _parse_command(command, [
            'IOPT',
            'L h',
            'V sig_s',
        ])
    elif i == '10':
        return _parse_command(command, [
            'IOPT',
            'l f_RF',
            'V phi_s IOP',
        ])
    assert False, 'unsupported CAVITE: {}'.format(i)

def _zgoubi_changref(command):
    if re.search(r'^(X|Y|Z)', command[1][0]):
        res = _parse_command_header(command)
        res['format'] = 'new'
        res['order'] = ' '.join(command[1])
        res['XCE'] = 0
        res['YCE'] = 0
        res['ALE'] = 0
        return res
    res = _parse_command(command, [
        'XCE YCE ALE',
    ])
    res['format'] = 'old'
    res['order'] = ''
    return res

def _zgoubi_drift(command):
    return _parse_command(command, [
        'l',
    ])

def _zgoubi_marker(command):
    return _parse_command_header(command)

def _zgoubi_multipol(command):
    res = _parse_command(command, [
        'IL',
        'l R_0 B_1 B_2 B_3 B_4 B_5 B_6 B_7 B_8 B_9 B_10',
        'X_E LAM_E E_2 E_3 E_4 E_5 E_6 E_7 E_8 E_9 E_10',
        'NCE C_0 C_1 C_2 C_3 C_4 C_5',
        'X_S LAM_S S_2 S_3 S_4 S_5 S_6 S_7 S_8 S_9 S_10',
        'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5',
        'R_1 R_2 R_3 R_4 R_5 R_6 R_7 R_8 R_9 R_10',
        'XPAS',
        'KPOS XCE YCE ALE',
    ])
    assert res['KPOS'] in ('1', '2', '3'), '{}: MULTIPOL KPOS not yet supported'.format(res['KPOS'])
    return res

def _zgoubi_objet(command):
    kobj = command[2][0]
    return None
    assert kobj == '5' or kobj == '5.1', '{}: only OBJET 5 and 5.1 is supported for now'.format(kobj)
    command_def = [
        'BORO',
        'KOBJ',
        'dY dT dZ dP dS dD',
        'YR TR ZR PR SR DR',
    ]
    if kobj == '5.1':
        command_def.append('alpha_Y beta_Y alpha_Z beta_Z alpha_S beta_S D_Y Dprime_Y D_Z Dprime_Z')
    return _parse_command(command, command_def)

def _zgoubi_particul(command):
    return None
    if re.search(r'^[\-\.0-9]+', command[1][0]):
        return _parse_command(command, [
            'M Q G TAU',
        ])
    return _parse_command(command, [
        'particle_type',
    ])

def _zgoubi_quadrupo(command):
    return _parse_command(command, [
        'IL',
        'l R_0 B_0',
        'X_E LAM_E',
        'NCE C_0 C_1 C_2 C_3 C_4 C_5',
        'X_S LAM_S',
        'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5',
        'XPAS',
        'KPOS XCE YCE ALE',
    ])

def _zgoubi_sextupol(command):
    return _zgoubi_quadrupo(command)

def _zgoubi_ymy(command):
    return _parse_command_header(command)
