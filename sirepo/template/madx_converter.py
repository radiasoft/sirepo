# -*- coding: utf-8 -*-
u"""Convert codes to/from MAD-X.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio, pkcollections, pkresource
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template.template_common import ParticleEnergy
from sirepo.template.lattice import LatticeUtil
import copy
import math
import sirepo.sim_data

_PI = 4 * math.atan(1)
_MADX_CONSTANTS = PKDict(
    pi=_PI,
    twopi=_PI * 2.0,
    raddeg=180.0 / _PI,
    degrad=_PI / 180.0,
    e=math.exp(1),
    emass=0.510998928e-03,
    pmass=0.938272046e+00,
    nmass=0.931494061+00,
    mumass=0.1056583715,
    clight=299792458.0,
    qelect=1.602176565e-19,
    hbar=6.58211928e-25,
    erad=2.8179403267e-15,
)

_MADX_SIM_DATA = sirepo.sim_data.get_class('madx')
_MADX_SCHEMA = _MADX_SIM_DATA.schema()

_MADX_VARIABLES = PKDict(
    twopi='pi * 2',
    raddeg='180 / pi',
    degrad='pi / 180',
)

_FIELD_MAP = PKDict(
    elegant=[
        #TODO(pjm): what is short MAD-X name, ex DRIFT or DRIF
        ['DRIFT',
            ['DRIF', 'l'],
            ['CSRDRIFT', 'l'],
            ['EDRIFT', 'l'],
            ['LSCDRIFT', 'l'],
        ],
        ['SBEND',
            ['CSBEND', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'tilt', 'hgap', 'fint'],
            ['SBEN', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'tilt', 'hgap', 'fint'],
            ['CSRCSBEND', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'tilt', 'hgap', 'fint'],
            ['KSBEND', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'tilt', 'hgap', 'fint'],
            ['NIBEND', 'l', 'angle', 'e1', 'e2', 'tilt', 'hgap', 'fint'],
        ],
        ['RBEND',
            ['RBEN', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'tilt', 'hgap', 'fint'],
            ['TUBEND', 'l', 'angle'],
        ],
        ['QUADRUPOLE',
            ['QUAD', 'l', 'k1', 'tilt'],
            ['KQUAD', 'l', 'k1', 'tilt'],
        ],
        ['SEXTUPOLE',
            ['SEXT', 'l', 'k2', 'tilt'],
            ['KSEXT', 'l', 'k2', 'tilt'],
        ],
        ['OCTUPOLE',
            ['OCTU', 'l', 'k3', 'tilt'],
            ['KOCT', 'l', 'k3', 'tilt'],
        ],
        ['SOLENOID',
            ['SOLE', 'l', 'ks'],
        ],
        ['MULTIPOLE',
            ['MULT', 'l=lrad', 'tilt', 'knl'],
        ],
        ['HKICKER',
            ['HKICK', 'l', 'kick', 'tilt'],
            ['EHKICK', 'l', 'kick', 'tilt'],
        ],
        ['VKICKER',
            ['VKICK', 'l', 'kick', 'tilt'],
            ['EVKICK', 'l', 'kick', 'tilt'],
        ],
        ['KICKER',
            ['KICKER', 'l', 'hkick', 'vkick', 'tilt'],
            ['EKICKER', 'l', 'hkick', 'vkick', 'tilt'],
        ],
        ['MARKER',
            ['MARK'],
        ],
        ['PLACEHOLDER',
            ['DRIF', 'l'],
        ],
        ['INSTRUMENT',
            ['DRIF', 'l'],
        ],
        ['ECOLLIMATOR',
            ['ECOL', 'l', 'x_max=aperture[0]', 'y_max=aperture[1]'],
        ],
        ['RCOLLIMATOR',
            ['RCOL', 'l', 'x_max=aperture[0]', 'y_max=aperture[1]'],
        ],
        ['COLLIMATOR apertype=ELLIPSE',
            ['ECOL', 'l', 'x_max=aperture[0]', 'y_max=aperture[1]'],
        ],
        ['COLLIMATOR apertype=RECTANGLE',
            ['RCOL', 'l', 'x_max=aperture[0]', 'y_max=aperture[1]'],
        ],
        ['RFCAVITY',
            ['RFCA', 'l', 'volt', 'freq'],
            ['MODRF', 'l', 'volt', 'freq'],
            ['RAMPRF', 'l', 'volt', 'freq'],
            ['RFCW', 'l', 'volt', 'freq'],
        ],
        ['TWCAVITY',
            ['RFDF', 'l', 'voltage=volt', 'frequency=freq'],
        ],
        ['HMONITOR',
            ['HMON', 'l'],
        ],
        ['VMONITOR',
            ['VMON', 'l'],
        ],
        ['MONITOR',
            ['MONI', 'l'],
            ['WATCH'],
        ],
        ['SROTATION',
            ['SROT', 'tilt=angle'],
        ],
    ],
    opal=[
        ['DRIFT',
            ['DRIFT', 'l'],
        ],
        ['SBEND',
            ['SBEND', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'hgap', 'tilt=psi'],
        ],
        ['RBEND',
            ['RBEND', 'l', 'angle', 'k1', 'k2', 'e1', 'e2', 'h1', 'h2', 'hgap', 'tilt=psi'],
        ],
        ['QUADRUPOLE',
            ['QUADRUPOLE', 'l', 'k1', 'k1s', 'tilt=psi'],
        ],
        ['SEXTUPOLE',
            ['SEXTUPOLE', 'l', 'k2', 'k2s', 'tilt=psi'],
        ],
        ['OCTUPOLE',
            ['OCTUPOLE', 'l', 'k3', 'k3s', 'tilt=psi'],
        ],
        ['SOLENOID',
         #TODO(pjm): compute dks from ksi?
            ['SOLENOID', 'l', 'ks'],
        ],
        ['MULTIPOLE',
         #TODO(pjm): compute kn, ks from knl, ksl?
            ['MULTIPOLE', 'l=lrad', 'tilt=psi'],
        ],
        ['HKICKER',
            ['HKICKER', 'l', 'kick', 'tilt=psi'],
        ],
        ['VKICKER',
            ['VKICKER', 'l', 'kick', 'tilt=psi'],
        ],
        ['KICKER',
            ['KICKER', 'l', 'hkick', 'vkick', 'tilt=psi'],
        ],
        ['MARKER',
            ['MARKER'],
        ],
        ['PLACEHOLDER',
            ['DRIF', 'l'],
        ],
        ['INSTRUMENT',
            ['INSTRUMENT', 'l'],
        ],
        ['ECOLLIMATOR',
            ['ECOLLIMATOR', 'l', 'xsize', 'ysize'],
        ],
        ['RCOLLIMATOR',
            ['RCOLLIMATOR', 'l', 'xsize', 'ysize'],
        ],
        ['COLLIMATOR apertype=ELLIPSE',
            ['ECOLLIMATOR', 'l', 'xsize=aperture[0]', 'ysize=aperture[1]'],
        ],
        ['COLLIMATOR apertype=RECTANGLE',
            ['RCOLLIMATOR', 'l', 'xsize=aperture[0]', 'ysize=aperture[1]'],
        ],
        ['RFCAVITY',
            ['RFCAVITY', 'l', 'volt', 'lag', 'harmon', 'freq'],
        ],
        ['HMONITOR',
            ['HMONITOR', 'l'],
        ],
        ['VMONITOR',
            ['VMONITOR', 'l'],
        ],
        ['MONITOR',
            ['MONITOR', 'l'],
        ],
        ['SROTATION',
            ['SROT', 'angle'],
        ],
    ],
)


def fixup_madx(madx, data=None):
    cv = code_variable.CodeVar(
        madx.models.rpnVariables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )
    assert LatticeUtil.has_command(madx, 'beam'), \
        'MAD-X file missing BEAM command'
    if not data:
        data = madx
    beam = LatticeUtil.find_first_command(madx, 'beam')
    beam_sub = beam.copy()
    rpns = [r.name for r in madx.models.rpnVariables]
    #pp = []
    for q in beam_sub:
        for n in rpns:
            if n in str(beam_sub[q]):
                beam_sub[q] = cv.eval_var_with_assert(beam[q])
                #pp.append(q)
                break
    #for p in pp:
    #    beam_sub[p] = cv.eval_var_with_assert(beam[p])
    if beam.energy == 1 and (beam.pc != 0 or beam.gamma != 0 or beam.beta != 0 or beam.brho != 0):
        # unset the default mad-x value if other energy fields are set
        beam.energy = 0
    particle = beam.particle.lower() or 'other'
    LatticeUtil.find_first_command(data, 'beam').particle = particle.upper()
    energy = ParticleEnergy.compute_energy('madx', particle, beam_sub)
    LatticeUtil.find_first_command(data, 'beam').pc = energy.pc
    t = LatticeUtil.find_first_command(data, 'track')
    if t:
        t.line = data.models.simulation.visualizationBeamlineId
    for el in data.models.elements:
        if el.type == 'SBEND' or el.type == 'RBEND':
            # mad-x is GeV (total energy), designenergy is MeV (kinetic energy)
            el.designenergy = round(
                (energy.energy - ParticleEnergy.PARTICLE[particle].mass) * 1e3,
                6,
            )
            # this is different than the opal default of "2 * sin(angle / 2) / length"
            # but matches elegant and synergia
            el.k0 = cv.eval_var_with_assert(el.angle) / cv.eval_var_with_assert(el.l)
            el.gap = 2 * cv.eval_var_with_assert(el.hgap)


def from_madx(to_sim_type, mad_data):
    return _convert(to_sim_type, mad_data, 'from')


def to_madx(from_sim_type, data):
    return _convert(from_sim_type, data, 'to')


def _convert(name, data, direction):
    if name == 'madx':
        return data
    assert name in _FIELD_MAP
    if direction == 'from':
        field_map = _FIELD_MAP[name].from_madx
        from_class = sirepo.sim_data.get_class('madx')
        to_class = sirepo.sim_data.get_class(name)
        drift_type = 'DRIFT'
    else:
        assert direction == 'to'
        field_map = _FIELD_MAP[name].to_madx
        from_class = sirepo.sim_data.get_class(name)
        to_class = sirepo.sim_data.get_class('madx')
        drift_type = _FIELD_MAP[name].from_madx.DRIFT[0]

    res = simulation_db.default_data(to_class.sim_type())
    for bl in data.models.beamlines:
        res.models.beamlines.append(PKDict(
            name=bl.name,
            items=bl['items'],
            id=bl.id,
        ))
    max_id = 0
    for el in data.models.elements:
        if el.type not in field_map:
            #TODO(pjm): convert to a sim appropriate drift rather than skipping
            pkdlog('Unhandled element type: {}', el.type)
            el.type = drift_type
            if 'l' not in el:
                el.l = 0
        fields = field_map[el.type]
        values = to_class.model_defaults(fields[0])
        values.name = el.name
        values.type = fields[0]
        values._id = el._id
        max_id = max(max_id, el._id)
        for idx in range(1, len(fields)):
            f1 = f2 = fields[idx]
            if '=' in fields[idx]:
                f1, f2 = fields[idx].split('=')
                if direction == 'from' and from_class.sim_type() == 'madx':
                    f2, f1 = f1, f2
            values[f1] = el[f2]
        # add any non-default values not in map to a comment
        comment = ''
        defaults = from_class.model_defaults(el.type)
        for f in el:
            if f not in fields and f in defaults and str(el[f]) != str(defaults[f]):
                v = el[f]
                if ' ' in str(v):
                    v = '"{}"'.format(v)
                comment += '{}={} '.format(f, v)
        if comment:
            values._comment = '{}: {} {}'.format(from_class.sim_type(), el.type, comment.strip())
        res.models.elements.append(values)
    res.models.rpnVariables = _rpn_variables(to_class, data)
    for f in ('name', 'visualizationBeamlineId', 'activeBeamlineId'):
        if f in data.models.simulation:
            res.models.simulation[f] = data.models.simulation[f]
    if direction == 'to' and to_class.sim_type() == 'madx':
        res.report = 'twissReport'
    return res


def _build_field_map(info):
    # builds a to/from madx fields map for each sim type
    res = PKDict()
    for sim in info.keys():
        res[sim] = PKDict(
            from_madx=PKDict(),
            to_madx=PKDict(),
        )
        for el in info[sim]:
            madx_name = el[0]
            res[sim].from_madx[madx_name] = el[1]
            for idx in range(1, len(el)):
                fields = copy.copy(el[idx])
                name = fields[0]
                if name not in res[sim].to_madx:
                    fields[0] = madx_name
                    res[sim].to_madx[name] = fields
    return res


def _rpn_variables(to_class, data):
    res = data.models.rpnVariables
    if to_class.sim_type() == 'madx':
        return list(filter(lambda x: x.name not in _MADX_VARIABLES, res))
    if to_class.sim_type() == 'opal':
        #TODO(pjm): opal already has these default vars, add config for this
        return res
    names = set([v.name for v in res])
    for name in _MADX_VARIABLES:
        if name not in names:
            res.append(PKDict(
                name=name,
                value=_MADX_VARIABLES[name],
            ))
    return res


_FIELD_MAP = _build_field_map(_FIELD_MAP)
