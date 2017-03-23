# -*- coding: utf-8 -*-
u"""Hellweg2D dump parser.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import ctypes
import math

_LIVE_PARTICLE = 0
_LOSS_VALUES = ['live', 'radius_lost', 'phase_lost', 'bz_lost', 'br_lost', 'bth_lost', 'beta_lost', 'step_lost']
_We0 = 0.5110034e6;

_PARTICLE_ACCESS = {
    'r': lambda p, lmb: abs(p.r * lmb),
    'th': lambda p, lmb: p.Th * 180.0 / math.pi,
    'x': lambda p, lmb: p.r * math.cos(p.Th) * lmb,
    'y': lambda p, lmb: p.r * math.sin(p.Th) * lmb,
    'br': lambda p, lmb: math.copysign(p.beta.r, p.r),
    'bth': lambda p, lmb: p.beta.th,
    'bx': lambda p, lmb: p.beta.r * math.cos(p.Th) - p.beta.th * math.sin(p.Th) * lmb,
    'by': lambda p, lmb: p.beta.r * math.sin(p.Th) + p.beta.th * math.cos(p.Th) * lmb,
    'bz': lambda p, lmb: p.beta.z,
    'ar': lambda p, lmb: math.atan2(p.beta.r, p.beta0),
    'ath': lambda p, lmb: math.atan2(p.beta.th, p.beta0),
    'ax': lambda p, lmb: math.atan2(p.beta.r * math.cos(p.Th) - p.beta.th * math.sin(p.Th) * lmb, p.beta.z),
    'ay': lambda p, lmb: math.atan2(p.beta.r * math.sin(p.Th) + p.beta.th * math.cos(p.Th) * lmb, p.beta.z),
    'az': lambda p, lmb: 0,
    'phi': lambda p, lmb: p.phi * 180.0 / math.pi,
    'zrel': lambda p, lmb: lmb * p.phi / (2 * math.pi),
    'z0': lambda p, lmb: p.z,
    'beta': lambda p, lmb: p.beta0,
    'w': lambda p, lmb: _velocity_to_mev(p.beta0),
}

_PARTICLE_LABEL = {
    'r': 'r [m]',
    'th': 'theta [deg]',
    'x': 'x [m]',
    'y': 'y [m]',
    # 'br': '',
    # 'bth': '',
    # 'bx': '',
    # 'by': '',
    # 'bz': '',
    'ar': 'r\' [rad]',
    'ath': 'theta\' [rad]',
    'ax': 'x\' [rad]',
    'ay': 'y\' [rad]',
    # 'az': '',
    'phi': 'phi [deg]',
    # 'zrel': '',
    # 'z0': '',
    # 'beta': '',
    'w': 'W [eV]',
}

class THeader(ctypes.Structure):
    _fields_ = [('NPoints', ctypes.c_int),
                ('NParticles', ctypes.c_int)]

class TField(ctypes.Structure):
    _fields_ = [('r', ctypes.c_double),
                ('th', ctypes.c_double),
                ('z', ctypes.c_double)]

class TStructure(ctypes.Structure):
    _fields_ = [('ksi', ctypes.c_double),
                ('lmb', ctypes.c_double),
                ('P', ctypes.c_double),
                ('dF', ctypes.c_double),
                ('E', ctypes.c_double),
                ('AF', ctypes.c_double),
                ('Rp', ctypes.c_double),
                ('B', ctypes.c_double),
                ('alpha', ctypes.c_double),
                ('betta', ctypes.c_double),
                ('Ra', ctypes.c_double),
                ('Hext', TField),
                ('jump', ctypes.c_bool),
                ('drift', ctypes.c_bool),
                ('CellNumber', ctypes.c_int)]

class TBeamHeader(ctypes.Structure):
    _fields_ = [('beam_lmb', ctypes.c_double),
                ('beam_h', ctypes.c_double),
                ('beam_current', ctypes.c_double),
                ('input_current', ctypes.c_double)]

class TParticle(ctypes.Structure):
    _fields_ = [('r', ctypes.c_double),
                ('Th', ctypes.c_double),
                ('beta', TField),
                ('phi', ctypes.c_double),
                ('z', ctypes.c_double),
                ('beta0', ctypes.c_double),
                ('lost', ctypes.c_int)]


def beam_info(filename, idx):
    info = {}
    with open (filename, 'rb') as f:
        header = THeader()
        assert f.readinto(header) == ctypes.sizeof(header)
        info['Header'] = header
        for i in range(header.NPoints):
            x = TStructure()
            assert f.readinto(x) == ctypes.sizeof(x)
            if i == idx:
                info['Structure'] = x
        info['Particles'] = []
        for i in range(header.NPoints):
            beam_header = TBeamHeader()
            assert f.readinto(beam_header) == ctypes.sizeof(beam_header)
            if i == idx:
                info['BeamHeader'] = beam_header
            for _ in range(header.NParticles):
                p = TParticle()
                assert f.readinto(p) == ctypes.sizeof(p)
                if i == idx:
                    info['Particles'].append(p)
        assert f.readinto(header) == 0
    assert 'Structure' in info
    return info


def get_label(field):
    return _PARTICLE_LABEL[field]


def get_points(info, field):
    res = []
    fn = _PARTICLE_ACCESS[field]
    lmb = info['BeamHeader'].beam_lmb

    for p in info['Particles']:
        if p.lost != _LIVE_PARTICLE:
            continue
        res.append(fn(p, lmb))
    return res


def _gamma_to_mev(g):
    return _We0 * (g - 1) * 1e-6


def _velocity_to_energy(b):
    return 1 / math.sqrt(1 - b ** 2)


def _velocity_to_mev(b):
    return _gamma_to_mev(_velocity_to_energy(b))
