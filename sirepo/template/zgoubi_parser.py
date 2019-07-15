# -*- coding: utf-8 -*-
u"""zgoubi input file parser.

l:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp, pkdc, pkdlog
import copy
import math
import re

_COMMAND_INDEX_POS = 110

_IGNORE_ELEMENTS = [
    'faisceau',
    'faiscnl',
    'fit',
    'images',
    'matrix',
    'optics',
    'options',
    'spnprnl',
    'spnprt',
    'spnstore',
    'system',
    'twiss',
]

_MAX_COORDINATES = 10

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
    lines = zgoubi_text.replace('\r', '').split('\n')
    elements = []
    # skip first documentation line
    title = lines.pop(0)
    unhandled_elements = {}
    current_command = None
    for line in lines:
        line = re.sub(r'\!.*$', '', line)
        line = re.sub(r'^\s+', '', line)
        line = re.sub(r'\s+$', '', line)
        if not line:
            continue
        keyword = _parse_keyword(line)
        if keyword:
            if current_command:
                _add_command(current_command, elements, unhandled_elements)
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


def parse_float(v):
    # replace fortran double precision format with normal exponential notation
    return float(re.sub(r'd|D', 'e', str(v)))


def tosca_file_count(el):
    if '-sf' in el.magnetType or ('-f' in el.magnetType and el['fileCount'] == 1):
        return 1
    if '-f' in el.magnetType:
        return el.fileCount
    if el.magnetType == '3d-mf-2v':
        return int(math.floor((int(el.IZ) + 1) / 2))
    if el.magnetType == '3d-mf-1v':
        return int(el.IZ)
    assert False, 'unhandled magnetType: {}'.format(el.magnetType)


def _add_command(command, elements, unhandled_elements):
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
    if 'label2' in res:
        if 'name' in res:
            res['name'] = '{} {}'.format(res['name'], res['label2'])
        else:
            res['name'] = res['label2']
        del res['label2']
    return res


def _parse_command_line(element, line, line_def):
    for k in line_def.split(' '):
        if k[0] == '*':
            k = k[1:]
            if not len(line):
                break
        assert len(line), 'Element "{} {}": missing "{}" value for line def: {}'.format(
            element['type'], element.get('name', ''), k, line_def)
        element[k] = line.pop(0)
    return element


def _parse_keyword(line):
    m = re.match(r"\s*'([\w\-]+)'", line)
    if m:
        res = m.group(1).upper()
        res = re.sub(r'-', '_', res)
        return res
    return None


def _parse_tosca_mesh_and_magnet_type(res):
    match = re.match(r'(\d+)\.(\d+)', res.mod)
    if match:
        mod = int(match.group(1))
        mod2 = int(match.group(2))
    else:
        mod = int(res.mod)
        mod2 = 0
    res.meshType = 'cartesian' if mod < 20 else 'cylindrical'
    res.magnetType = '2d' if res.IZ == '1' else '3d'
    if mod == 12 and mod2 == 2:
        res.magnetType += '-2f'
    elif mod == 0:
        res.magnetType += '-sf' if res.magnetType == '2d' else '-mf'
    elif mod in (3, 12, 20, 24):
        res.magnetType += '-sf'
    elif mod in (1, 15, 25, 22):
        res.magnetType += '-mf'
    else:
        assert False, 'unsupported TOSCA, MOD: {}'.format(res.mod)
    if mod == 3:
        res.magnetType += '-ags'
        if mod2 == 1:
            res.magnetType += '-p'
    elif mod in (15, 22, 25):
        res.magnetType += '-f'
    if mod == 1 or (mod == 12 and mod2 == 1):
        res.magnetType += '-1v'
    elif mod == 22 or (mod == 0 and res.IZ != '1') or (mod == 12 and not mod2):
        res.magnetType += '-2v'
    elif mod == 12 and mod2 == 2:
        res.magnetType += '-8v'
    elif mod == 20:
        res.magnetType += '-4v'
    res.fileCount = mod2


def _parse_tosca_title(res, title):
    m = re.match(r'\bFLIP\b', title)
    if m:
        res.flipX = '1'
        title = re.sub('\bFLIP\b', ' ', title)
    m = re.match(r'\bHEADER_(\d+)', title)
    if m:
        res.headerLineCount = int(m.group(1))
        title = re.sub(r'\bHEADER_\d+\b', ' ', title)
    else:
        # tosca default header line count...
        res.headerLineCount = 8
    m = re.match(r'\bZroBXY\b', title)
    if m:
        res.zeroBXY = '1'
        title = re.sub('\bZroBXY\b', ' ', title)
    m = re.match(r'\bRHIC_helix\b', title)
    if m:
        res.normalizeHelix = '1'
        title = re.sub('\bRHIC_helix\b', ' ', title)
    if 'name' not in res:
        title = re.sub(r'^\s+|\s+$', '', title)
        title = re.sub(r'\s+', ' ', title)
        res.name = title


def _remove_fields(model, fields):
    for f in fields:
        if f in model:
            del model[f]
    return model


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
    _remove_fields(res, ['NCE', 'NCS'])
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
    assert False, 'unsupported CAVITE IOPT: {}'.format(iopt)


def _zgoubi_changref(command):
    if re.search(r'^(X|Y|Z)', command[1][0]):
        # new format CHANGREF --> CHANGREF2
        res = _parse_command_header(command)
        res['type'] = 'CHANGREF2'
        res['subElements'] = []
        for i in range(int(len(command[1]) / 2)):
            v = parse_float(command[1][i * 2 + 1])
            if v != 0:
                res['subElements'].append(pkcollections.Dict({
                    'type': 'CHANGREF_VALUE',
                    'transformType': command[1][i * 2],
                    'transformValue': v,
                }))
        if not len(res['subElements']):
            return None
        return res
    return _parse_command(command, [
        'XCE YCE ALE',
    ])


def _zgoubi_drift(command):
    return _parse_command(command, [
        'l',
    ])


def _zgoubi_esl(command):
    res = _zgoubi_drift(command)
    res['type'] = 'DRIFT'
    return res


def _zgoubi_faistore(command):
    res = _parse_command(command, [
        'file',
        'ip',
    ])
    _remove_fields(res, ['name', 'file'])
    if int(res['ip']) < 1:
        res['ip'] = 1
    res['type'] = 'simulationSettings'
    return res


def _zgoubi_ffag(command, dipole_type=None, dipole_def=None):
    res = _parse_command(command, [
        'IL',
        'N AT RM'
    ])
    if not dipole_def:
        dipole_def = [
            'ACN DELTA_RM BZ_0 K',
            'G0_E KAPPA_E',
            'NCE CE_0 CE_1 CE_2 CE_3 CE_4 CE_5 SHIFT_E',
            'OMEGA_E THETA_E R1_E U1_E U2_E R2_E',
            'G0_S KAPPA_S',
            'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5 SHIFT_S',
            'OMEGA_S THETA_S R1_S U1_S U2_S R2_S',
            'G0_L KAPPA_L',
            'NCL CL_0 CL_1 CL_2 CL_3 CL_4 CL_5 SHIFT_L',
            'OMEGA_L THETA_L R1_L U1_L U2_L R2_L',
        ]
    res['dipoles'] = []
    dipole_count = int(res['N'])
    def_size = len(dipole_def)
    for idx in range(dipole_count):
        dipole = pkcollections.Dict({
            'type': dipole_type if dipole_type else 'ffaDipole',
        })
        res['dipoles'].append(dipole)
        for line_idx in range(len(dipole_def)):
            _parse_command_line(dipole, command[3 + def_size * idx + line_idx], dipole_def[line_idx])
        _remove_fields(dipole, ['NCE', 'NCS', 'NCL'])
    _parse_command_line(res, command[3 + def_size * dipole_count], 'KIRD RESOL')
    _parse_command_line(res, command[3 + def_size * dipole_count + 1], 'XPAS')
    # 'KPOS DP' or 'KPOS RE TE RS TS'
    _parse_command_line(res, command[3 + def_size * dipole_count + 2], 'KPOS RE *TE *RS *TS')
    if res['KPOS'] == '1':
        res['DP'] = res['RE']
        _remove_fields(res, ['RE', 'TE', 'RS', 'TS'])
    res['type'] = 'FFA'
    return res


def _zgoubi_ffag_spi(command):
    res = _zgoubi_ffag(command, 'ffaSpiDipole', [
        'ACN DELTA_RM BZ_0 K',
        'G0_E KAPPA_E',
        'NCE CE_0 CE_1 CE_2 CE_3 CE_4 CE_5 SHIFT_E',
        'OMEGA_E XI_E',
        'G0_S KAPPA_S',
        'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5 SHIFT_S',
        'OMEGA_S XI_S',
        'G0_L KAPPA_L',
        'NCL CL_0 CL_1 CL_2 CL_3 CL_4 CL_5 SHIFT_L',
        'OMEGA_L XI_L',
    ])
    res['type'] = 'FFA_SPI'
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
    _remove_fields(res, ['NCE', 'NCS'])
    assert res['KPOS'] in ('1', '2', '3'), '{}: MULTIPOL KPOS not yet supported'.format(res['KPOS'])
    return res


def _zgoubi_objet(command):
    res = _parse_command(command, [
        'rigidity',
        'KOBJ'
    ])
    kobj = res['KOBJ']
    _remove_fields(res, ['KOBJ', 'name'])
    res['type'] = 'bunch'
    if kobj == '2' or kobj == '2.1':
        imax = int(command[3][0])
        coordinates = []
        for idx in range(imax):
            coord = _parse_command_line({}, command[4 + idx], 'Y T Z P X D')
            coord['type'] = 'particleCoordinate'
            coordinates.append(coord)
        if len(coordinates) > _MAX_COORDINATES:
            coordinates = coordinates[:_MAX_COORDINATES]
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
    if 'n_cutoff2_Y' in res and parse_float(res['n_cutoff_Y']) >= 0:
        res['DT'] = res['DY']
        res['DY'] = res['n_cutoff2_Y']
    if 'n_cutoff2_Z' in res and parse_float(res['n_cutoff_Z']) >= 0:
        res['DP'] = res['DZ']
        res['DZ'] = res['n_cutoff2_Z']
    _remove_fields(res, ['KOBJ', 'name'])
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
    _remove_fields(res, ['name'])
    res['type'] = 'particle'
    return res


def _zgoubi_quadrupo(command):
    res = _parse_command(command, [
        'IL',
        'l R_0 B_0',
        'X_E LAM_E',
        'NCE C_0 C_1 C_2 C_3 C_4 C_5',
        'X_S LAM_S',
        'NCS CS_0 CS_1 CS_2 CS_3 CS_4 CS_5',
        'XPAS',
        'KPOS XCE YCE ALE',
    ])
    _remove_fields(res, ['NCE', 'NCS'])
    return res


def _zgoubi_rebelote(command):
    res = _parse_command(command, [
        'npass',
    ])
    res['npass'] = int(res['npass']) + 1
    res['type'] = 'simulationSettings'
    return res


def _zgoubi_scaling(command):
    #TODO(pjm): access IOPT and NFAM directly from command before calling _parse_command
    command2 = copy.deepcopy(command)
    pattern = [
        'IOPT NFAM',
    ]
    res = _parse_command(command, pattern)
    for idx in range(1, int(res['NFAM']) + 1):
        pattern.append('NAMEF{} *LBL{}'.format(idx, idx))
        pattern.append('ignore'.format(idx))
        pattern.append('SCL{}'.format(idx))
        pattern.append('ignore'.format(idx))
    res = _parse_command(command2, pattern)
    _remove_fields(res, ['NFAM', 'ignore'])
    return res


def _zgoubi_sextupol(command):
    return _zgoubi_quadrupo(command)


def _zgoubi_solenoid(command):
    res = _parse_command(command, [
        'IL',
        'l R_0 B_0 *MODL',
        'X_E X_S',
        'XPAS',
        'KPOS XCE YCE ALE',
    ])
    return res


def _zgoubi_spinr(command):
    iopt = command[1][0]
    if iopt == '0':
        format = ['IOPT']
    elif iopt == '1':
        format = [
            'IOPT',
            'phi mu'
        ]
    elif iopt == '2':
        format = [
            'IOPT',
            'phi B B_0 C_0 C_1 C_2 C_3',
        ]
    else:
        assert False, 'unknown SPINR IOPT: {}'.format(iopt)
    return _parse_command(command, format)


def _zgoubi_spntrk(command):
    kso = command[1][0]
    res = {
        'KSO': '1',
        'S_X': 0,
        'S_Y': 0,
        'S_Z': 0,
        'type': 'SPNTRK',
    }
    if kso == '0':
        res['KSO'] = '0'
    if kso == '1':
        res['S_X'] = 1
    elif kso == '2':
        res['S_Y'] = 1
    elif kso == '3':
        res['S_Z'] = 1
    elif re.search(r'^4', kso):
        res = _parse_command(command, [
            'KSO',
            'S_X S_Y S_Z',
        ])
        if res['KSO'] != '0':
            res['KSO'] = '1'
        _remove_fields(res, ['name'])
    return res


def _zgoubi_srloss(command):
    res = _parse_command(command, [
        'KSR',
        'STR1',
    ])
    res['KSR'] = re.sub(r'\..*$', '', res['KSR'])
    if res['STR1'] == 'all':
        res['applyToAll'] = '1'
    else:
        res['keyword'] = res['STR1']
    _remove_fields(res, ['STR1', 'name'])
    return res


def _zgoubi_tosca(command):
    title = ' '.join(command[3])
    res = _parse_command(command, [
        'IC IL',
        'BNORM XN YN ZN',
        'TITL',
        'IX IY IZ mod *field1 *field2 *field3 *field4',
    ])
    _parse_tosca_mesh_and_magnet_type(res)
    _parse_tosca_title(res, title)
    res.fileNames = []
    file_count = tosca_file_count(res)
    for idx in range(file_count):
        el = {}
        #TODO(pjm): _parse_command_line() should remove line, can then remove 5 offset
        _parse_command_line(el, command[5 + idx], 'FNAME')
        res.fileNames.append(el['FNAME'])
    _parse_command_line(res, command[5 + file_count], 'ID A B C *Ap *Bp *Cp *App *Bpp *Cpp')
    _parse_command_line(res, command[6 + file_count], 'IORDRE')
    _parse_command_line(res, command[7 + file_count], 'XPAS')
    if res.meshType == 'cartesian':
        _parse_command_line(res, command[8 + file_count], 'KPOS XCE YCE ALE')
    else:
        _parse_command_line(res, command[8 + file_count], 'KPOS')
        _parse_command_line(res, command[9 + file_count], 'RE TE RS TS')
    _remove_fields(res, ['mod', 'IC', 'TITL'])
    return res


def _zgoubi_ymy(command):
    return _parse_command_header(command)
