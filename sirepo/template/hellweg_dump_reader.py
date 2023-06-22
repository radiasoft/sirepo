# -*- coding: utf-8 -*-
"""Hellweg dump parser.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern.pkcollections import PKDict
import ctypes
import math

_LIVE_PARTICLE = 0
_LOSS_VALUES = [
    "live",
    "radius_lost",
    "phase_lost",
    "bz_lost",
    "br_lost",
    "bth_lost",
    "beta_lost",
    "step_lost",
]
_STRUCTURE_VALUES = [
    "ksi",
    "z",
    "a",
    "rp",
    "alpha",
    "sbeta",
    "ra",
    "rb",
    "bz_ext",
    "br_ext",
    "num",
    "e0",
    "ereal",
    "prf",
    "pbeam",
    "bbeta",
    "wav",
    "wmax",
    "xb",
    "yb",
    "er",
    "ex",
    "ey",
    "enr",
    "enx",
    "eny",
    "e4d",
    "e4dn",
    "et",
    "ent",
]

_W0_PARTICLE_CONSTANT = PKDict(
    electrons=0.5110034e6,
    protons=938.272013e6,
    ions=931.494028e6,
)

_BEAM_PARAMETER = {
    # mod() in hellweg means abs()
    "r": lambda p, lmb: abs(p.r * lmb),
    "th": lambda p, lmb: p.Th * 180.0 / math.pi,
    "x": lambda p, lmb: p.r * math.cos(p.Th) * lmb,
    "y": lambda p, lmb: p.r * math.sin(p.Th) * lmb,
    "ar": lambda p, lmb: math.atan2(p.gb.r, math.sqrt(p.g**2 - 1)),
    "ath": lambda p, lmb: math.atan2(p.gb.th, math.sqrt(p.g**2 - 1)),
    "ax": lambda p, lmb: math.atan2(
        p.gb.r * math.cos(p.Th) - p.gb.th * math.sin(p.Th), p.gb.z
    ),
    "ay": lambda p, lmb: math.atan2(
        p.gb.r * math.sin(p.Th) + p.gb.th * math.cos(p.Th), p.gb.z
    ),
    "az": lambda p, lmb: 0,
    "phi": lambda p, lmb: p.phi * 180.0 / math.pi,
    "zrel": lambda p, lmb: lmb * p.phi / (2 * math.pi),
    "z0": lambda p, lmb: p.z,
    "w": lambda p, lmb: p.g,
}

_STRUCTURE_PARAMETER = {
    "z": lambda s: s.ksi * s.lmb,
}

_STRUCTURE_TITLE = {
    "wav": "Average Energy",
    "wmax": "Maximum Energy",
    "bbeta": "Beam Velocity",
    "sbeta": "Phase Velocity",
    "ra": "Aperture",
    "rb": "Beam Radius (rms)",
    "pbeam": "Beam Power",
    "prf": "RF Power",
    "e0": "With Beam Load",
    "ereal": "Without Beam Load",
    "er": "Actual (rms)",
    "enr": "Normalized (rms)",
    "ex": "Actual (rms)",
    "enx": "Normalized (rms)",
    "ey": "Actual (rms)",
    "eny": "Normalized (rms)",
    "e4d": "Actual (rms)",
    "e4dn": "Normalized (rms)",
    "et": "Actual (rms)",
    "ent": "Normalized (rms)",
}

_STRUCTURE_LABEL = {
    "wav": "W [eV]",
    "sbeta": "Beta",
    "rb": "r [m]",
    "prf": "P [W]",
    "e0": "E, (MV/m)",
    "er": "er [m]",
    "ex": "ex [m]",
    "ey": "ey [m]",
    "e4d": "e4D [m]",
    "et": "eth [m]",
    "z": "z [m]",
}

_PARTICLE_LABEL = {
    "r": "r [m]",
    "th": "theta [deg]",
    "x": "x [m]",
    "y": "y [m]",
    "ar": "r' [rad]",
    "ath": "theta' [rad]",
    "ax": "x' [rad]",
    "ay": "y' [rad]",
    "phi": "phi [deg]",
    "z0": "z [m]",
    "w": "W [eV]",
}

# some values are pointers which would never serialize correctly
# the same size in bytes as a long integer
_POINTER_TYPE = ctypes.c_long


class TDimension(ctypes.Structure):
    _fields_ = [
        ("Nx", ctypes.c_int),
        ("Ny", ctypes.c_int),
        ("Nz", ctypes.c_int),
    ]


class TPivot(ctypes.Structure):
    _fields_ = [("X", _POINTER_TYPE), ("Y", _POINTER_TYPE), ("Z", _POINTER_TYPE)]


class TFieldMap2D(ctypes.Structure):
    _fields_ = [("Dim", TDimension), ("Piv", TPivot), ("Field", _POINTER_TYPE)]


class THeader(ctypes.Structure):
    _fields_ = [("NPoints", ctypes.c_int), ("NParticles", ctypes.c_int)]


class TField(ctypes.Structure):
    _fields_ = [("r", ctypes.c_double), ("th", ctypes.c_double), ("z", ctypes.c_double)]


class TStructure(ctypes.Structure):
    _fields_ = [
        ("ksi", ctypes.c_double),
        ("lmb", ctypes.c_double),
        ("P", ctypes.c_double),
        ("dF", ctypes.c_double),
        ("E", ctypes.c_double),
        ("AF", ctypes.c_double),
        ("Rp", ctypes.c_double),
        ("B", ctypes.c_double),
        ("alpha", ctypes.c_double),
        ("betta", ctypes.c_double),
        ("Ra", ctypes.c_double),
        ("Bmap", TFieldMap2D),
        ("jump", ctypes.c_bool),
        ("drift", ctypes.c_bool),
        ("CellNumber", ctypes.c_int),
    ]


class TBeamHeader(ctypes.Structure):
    _fields_ = [
        ("beam_lmb", ctypes.c_double),
        ("beam_h", ctypes.c_double),
        ("beam_current", ctypes.c_double),
        ("input_current", ctypes.c_double),
    ]


class TParticle(ctypes.Structure):
    _fields_ = [
        ("r", ctypes.c_double),
        ("Th", ctypes.c_double),
        ("z", ctypes.c_double),
        ("gb", TField),
        ("g", ctypes.c_double),
        ("phi", ctypes.c_double),
        ("lost", ctypes.c_int),
    ]


def beam_header(filename):
    with open(filename, "rb") as f:
        header = THeader()
        assert f.readinto(header) == ctypes.sizeof(header)
        return header


def beam_info(filename, idx):
    info = {}
    with open(filename, "rb") as f:
        header = THeader()
        assert f.readinto(header) == ctypes.sizeof(header)
        info["Header"] = header
        structure = TStructure()
        size = ctypes.sizeof(structure)
        if idx > 0:
            f.seek(idx * size, 1)
        assert f.readinto(structure) == size
        info["Structure"] = structure
        if idx < header.NPoints - 1:
            f.seek((header.NPoints - idx - 1) * size, 1)
        beam_header = TBeamHeader()
        size = (
            ctypes.sizeof(beam_header) + ctypes.sizeof(TParticle()) * header.NParticles
        )
        if idx > 0:
            f.seek(idx * size, 1)
        assert f.readinto(beam_header) == ctypes.sizeof(beam_header)
        info["BeamHeader"] = beam_header
        particles = []
        for _ in range(header.NParticles):
            p = TParticle()
            assert f.readinto(p) == ctypes.sizeof(p)
            particles.append(p)
        info["Particles"] = particles
        # ensure the expected bytes are present
        if idx < header.NPoints - 1:
            f.seek(
                (header.NPoints - idx - 1)
                * (ctypes.sizeof(beam_header) + ctypes.sizeof(p) * header.NParticles),
                1,
            )
        # must have reached end of file or bin format has changed
        assert f.readinto(header) == 0
    return info


def get_label(field):
    return _PARTICLE_LABEL[field]


def get_parameter(info, field):
    fn = _STRUCTURE_PARAMETER[field]
    return fn(info["Structure"])


def get_parameter_label(field):
    return _STRUCTURE_LABEL[field]


def get_parameter_title(field):
    return _STRUCTURE_TITLE[field]


def get_points(info, field, particle_species):
    res = []
    fn = _BEAM_PARAMETER[field]
    lmb = info["BeamHeader"].beam_lmb

    for p in info["Particles"]:
        if p.lost == _LIVE_PARTICLE:
            res.append(_apply_beam_fn(field, fn, p, lmb, particle_species))
    return res


def parameter_index(name):
    return _STRUCTURE_VALUES.index(name)


def particle_info(filename, field, count, particle_species):
    info = {}
    with open(filename, "rb") as f:
        header = THeader()
        assert f.readinto(header) == ctypes.sizeof(header)
        info["Header"] = header
        if count > header.NPoints:
            count = header.NPoints
        z_values = []
        yfn = _BEAM_PARAMETER[field]
        zfn = _STRUCTURE_PARAMETER["z"]
        for _ in range(header.NPoints):
            structure = TStructure()
            assert f.readinto(structure) == ctypes.sizeof(structure)
            z_values.append(zfn(structure))
        info["z_values"] = z_values
        beam_header_size = ctypes.sizeof(TBeamHeader())
        particle_size = ctypes.sizeof(TParticle())
        y_map = {}
        indices = []
        for i in range(count):
            idx = int(round((i * header.NParticles) / count))
            y_map[idx] = []
            indices.append(idx)
        y_range = None

        for _ in range(header.NPoints):
            beam_header = TBeamHeader()
            assert f.readinto(beam_header) == beam_header_size
            lmb = beam_header.beam_lmb
            pi = 0
            for idx in indices:
                assert idx >= pi
                if idx > pi:
                    f.seek((idx - pi) * particle_size, 1)
                p = TParticle()
                assert f.readinto(p) == particle_size
                if p.lost == _LIVE_PARTICLE:
                    v = _apply_beam_fn(field, yfn, p, lmb, particle_species)
                    y_map[idx].append(v)
                    if y_range:
                        if v < y_range[0]:
                            y_range[0] = v
                        elif v > y_range[1]:
                            y_range[1] = v
                    else:
                        y_range = [v, v]
                pi = idx + 1
            if pi < header.NParticles:
                f.seek((header.NParticles - pi) * particle_size, 1)
        assert f.readinto(header) == 0
        y_values = []
        for idx in sorted(y_map.keys()):
            y_values.append(y_map[idx])
        info["y_values"] = y_values
        info["y_range"] = y_range
    return info


def _apply_beam_fn(field, fn, p, lmb, species):
    if field == "w":
        return _gamma_to_ev(fn(p, lmb), species)
    return fn(p, lmb)


def _gamma_to_ev(g, species):
    return _W0_PARTICLE_CONSTANT[species] * (g - 1)
