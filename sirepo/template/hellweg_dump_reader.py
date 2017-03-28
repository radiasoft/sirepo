# -*- coding: utf-8 -*-
u"""Hellweg dump parser.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import ctypes
import math

_LIVE_PARTICLE = 0
_LOSS_VALUES = ['live', 'radius_lost', 'phase_lost', 'bz_lost', 'br_lost', 'bth_lost', 'beta_lost', 'step_lost']
_We0 = 0.5110034e6

_BEAM_PARAMETER = {
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

_STRUCTURE_PARAMETER = {
    'z': lambda s: s.ksi * s.lmb,
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


def beam_header(filename):
    with open (filename, 'rb') as f:
        header = THeader()
        assert f.readinto(header) == ctypes.sizeof(header)
        return header


def beam_info(filename, idx):
    info = {}
    with open (filename, 'rb') as f:
        header = THeader()
        assert f.readinto(header) == ctypes.sizeof(header)
        info['Header'] = header
        structure = TStructure()
        size = ctypes.sizeof(structure)
        if idx > 0:
            f.seek(idx * size, 1)
        assert f.readinto(structure) == size
        info['Structure'] = structure
        if idx < header.NPoints - 1:
            f.seek((header.NPoints - idx - 1) * size, 1)
        info['Particles'] = []
        beam_header = TBeamHeader()
        size = ctypes.sizeof(beam_header) + ctypes.sizeof(TParticle()) * header.NParticles
        if idx > 0:
            f.seek(idx * size, 1)
        assert f.readinto(beam_header) == ctypes.sizeof(beam_header)
        info['BeamHeader'] = beam_header
        particles = []
        for _ in xrange(header.NParticles):
            p = TParticle()
            assert f.readinto(p) == ctypes.sizeof(p)
            particles.append(p)
        info['Particles'] = particles
    return info


def get_label(field):
    return _PARTICLE_LABEL[field]


def get_parameter(info, field):
    fn = _STRUCTURE_PARAMETER[field]
    return fn(info['Structure'])


def get_points(info, field):
    res = []
    fn = _BEAM_PARAMETER[field]
    lmb = info['BeamHeader'].beam_lmb

    for p in info['Particles']:
        if p.lost == _LIVE_PARTICLE:
            res.append(fn(p, lmb))
    return res


def _gamma_to_mev(g):
    return _We0 * (g - 1) * 1e-6


def _velocity_to_energy(b):
    return 1 / math.sqrt(1 - b ** 2)


def _velocity_to_mev(b):
    return _gamma_to_mev(_velocity_to_energy(b))
