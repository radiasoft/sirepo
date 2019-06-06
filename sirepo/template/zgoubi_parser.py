# -*- coding: utf-8 -*-
u"""zgoubi input file parser.

l:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template.line_parser import LineParser
import copy
import re

_COMMAND_INDEX_POS = 110

_CHANGREF_MAP = {
    'XS': 'XCE',
    'YS': 'YCE',
    'ZR': 'ALE',
}

_IGNORE_ELEMENTS = [
    'faisceau',
    'images',
]

#TODO(pjm): remove when we have updated to latest zgoubi
_NEW_PARTICLE_TYPES = {
    'POSITRON': {
        'M': 0.5109989461,
        'Q': 1.602176487e-19,
        'G': 1.159652181e-3,
        'Tau': 1e99,
    },
}

def parse_file(zgoubi_text, max_id=0):
    parser = LineParser(max_id)
    lines = zgoubi_text.replace('\r', '').split('\n')
    elements = []
    # skip first documentation line
    title = lines.pop(0)
    parser.increment_line_number()
    unhandled_elements = {}
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
                _add_command(parser, current_command, elements, unhandled_elements)
            if keyword == 'END' or keyword == 'FIN':
                current_command = None
                break
            line = _strip_command_index(line)
            current_command = [line.split()]
            current_command[0][0] = keyword
        else:
            line = line.lstrip()
            current_command.append(line.split())
    assert current_command is None, 'missing END element'
    return title, elements, sorted(unhandled_elements.keys())


def _add_command(parser, command, elements, unhandled_elements):
    command_type = command[0][0]
    if command_type.lower() in _IGNORE_ELEMENTS:
        return
    method = '_zgoubi_{}'.format(command_type).lower()
    if method not in globals():
        unhandled_elements[command_type] = True
        # replace the element with a zero length drift
        command = [['DRIFT', 'DUMMY {}'.format(command_type)], ['0']]
        method = '_zgoubi_drift'
    el = globals()[method](command)
    if el:
        if type(el) == list:
            elements += el
        else:
            elements.append(el)


def _parse_command(command, command_def):
    res = _parse_command_header(command)
    for i in range(len(command_def)):
        _parse_command_line(res, command[i + 1], command_def[i])
    return res


def _parse_command_header(command):
    res = _parse_command_line(pkcollections.Dict({}), command[0], 'type *name *label2')
    for f in ('name', 'label2'):
        # don't parse line numbers into name or label2
        if f in res and re.search(r'^\d+$', res[f]):
            del res[f]
    return res


def _parse_command_line(element, line, line_def):
    for k in line_def.split(' '):
        if k[0] == '*':
            k = k[1:]
            if not len(line):
                break
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
    iopt = re.sub(r'\..*$', '', command[1][0])
    command[1][0] = iopt
    if iopt == '0' or iopt == '1':
        return _parse_command(command, [
            'IOPT',
            'L h',
            'V',
        ])
    if iopt == '2' or iopt == '3':
        return _parse_command(command, [
            'IOPT',
            'L h',
            'V sig_s',
        ])
    if iopt == '7':
        return _parse_command(command, [
            'IOPT',
            'L f_RF',
            'V sig_s',
        ])
    if iopt == '10':
        return _parse_command(command, [
            'IOPT',
            'l f_RF *ID',
            'V sig_s IOP',
        ])
    assert False, 'unsupported CAVITE: {}'.format(i)


def _zgoubi_changref(command):
    if re.search(r'^(X|Y|Z)', command[1][0]):
        # convert new format CHANGREF to a series of old format elements
        el = _parse_command_header(command)
        el['XCE'] = el['YCE'] = el['ALE'] = 0
        res = []
        for i in range(int(len(command[1]) / 2)):
            name = command[1][i * 2]
            value = float(command[1][i * 2 + 1])
            if value == 0:
                continue
            if name in _CHANGREF_MAP:
                el2 = el.copy()
                el2[_CHANGREF_MAP[name]] = value
                res.append(el2)
            else:
                pkdlog('zgoubi CHANGEREF skipping: {}={}', name, value)
        return res
    res = _parse_command(command, [
        'XCE YCE ALE',
    ])
    return res


def _zgoubi_drift(command):
    return _parse_command(command, [
        'l',
    ])


def _zgoubi_esl(command):
    res = _zgoubi_drift(command)
    res['type'] = 'DRIFT'
    return res


def _zgoubi_marker(command):
    res = _parse_command_header(command)
    res['plt'] = '0'
    return res


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
    res = _parse_command(command, [
        'rigidity',
        'KOBJ'
    ])
    kobj = res['KOBJ']
    del res['KOBJ']
    if 'name' in res:
        del res['name']
    res['type'] = 'bunch'
    if kobj == '2' or kobj == '2.1':
        coordinates = []
        for i in range(4, len(command) - 1):
            coord = _parse_command_line({}, command[i], 'Y T Z P X D')
            for k in coord:
                coord[k] = float(coord[k])
                if kobj == '2':
                    if k in ('Y', 'Z', 'S'):
                        coord[k] *= 1e-2
                    elif k in ('T', 'P'):
                        coord[k] *= 1e-3
            coordinates.append(coord)
        res.particleCount2 = len(coordinates)
        res.method = 'OBJET2.1'
        res.coordinates = coordinates
    return res


def _zgoubi_mcobjet(command):
    kobj = command[2][0]
    assert kobj == '3', '{}: only MCOBJET 3 is supported for now'.format(kobj)
    res = _parse_command(command, [
        'rigidity',
        'KOBJ',
        'particleCount',
        'KY KT KZ KP KX KD',
        'Y0 T0 Z0 P0 X0 D0',
        'alpha_Y beta_Y emit_Y n_cutoff_Y *n_cutoff2_Y *DY *DT',
        'alpha_Z beta_Z emit_Z n_cutoff_Z *n_cutoff2_Z *DZ *DP',
        'alpha_X beta_X emit_X n_cutoff_X *n_cutoff2_X',
        # 'IR1 IR2 IR3',
    ])
    if 'n_cutoff2_Y' in res and float(res['n_cutoff_Y']) >= 0:
        res['DT'] = res['DY']
        res['DY'] = res['n_cutoff2_Y']
    if 'n_cutoff2_Z' in res and float(res['n_cutoff_Z']) >= 0:
        res['DP'] = res['DZ']
        res['DZ'] = res['n_cutoff2_Z']
    del res['KOBJ']
    if 'name' in res:
        del res['name']
    res['type'] = 'bunch'
    return res


def _zgoubi_particul(command):
    if re.search(r'^[\-\.0-9]+', command[1][0]):
        res = _parse_command(command, [
            'M Q G Tau',
        ])
        res['particleType'] = 'Other'
    else:
        res = _parse_command(command, [
            'particleType',
        ])
        if res['particleType'] in _NEW_PARTICLE_TYPES:
            res.update(_NEW_PARTICLE_TYPES[res['particleType']])
            res['particleType'] = 'Other'
    if 'name' in res:
        del res['name']
    res['type'] = 'particle'
    return res


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


def _zgoubi_scaling(command):
    command2 = copy.deepcopy(command)
    pattern = [
        'IOPT NFAM',
    ]
    res = _parse_command(command, pattern)
    for idx in range(1, int(res['NFAM']) + 1):
        pattern.append('NAMEF{}'.format(idx))
        pattern.append('ignore'.format(idx))
        pattern.append('SCL{}'.format(idx))
        pattern.append('ignore'.format(idx))
    res = _parse_command(command2, pattern)
    del res['NFAM']
    del res['ignore']
    return res


def _zgoubi_sextupol(command):
    return _zgoubi_quadrupo(command)


def _zgoubi_ymy(command):
    return _parse_command_header(command)
