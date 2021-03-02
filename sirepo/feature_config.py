# -*- coding: utf-8 -*-
u"""List of features available

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# defer all imports so *_CODES is available to testing functions

#: Codes that depend on other codes. [x][0] depends on [x][1]
_DEPENDENT_CODES = [
    ['jspec', 'elegant'],
    ['controls', 'madx'],
]

#: Codes on prod
_PROD_FOSS_CODES = frozenset((
    'elegant',
    'jspec',
    'madx',
    'ml',
    'opal',
    'radia',
    'shadow',
    'srw',
    'synergia',
    'warppba',
    'warpvnd',
    'webcon',
    'zgoubi',
))

#: Codes on dev, alpha, and beta
_NON_PROD_FOSS_CODES = frozenset((
    'controls',
    'irad',
    'myapp',
    'rcscon',
    'rs4pi',
    'silas',
))

#: All possible open source codes
_FOSS_CODES = _PROD_FOSS_CODES.union(_NON_PROD_FOSS_CODES)

#: codes for which we default to giving the user authorization but it can be revoked
_DEFAULT_PROPRIETARY_CODES = frozenset(('jupyterhublogin',))

#: codes for which we require dynamically loaded binaries
_PROPRIETARY_CODES = frozenset(('flash',))

#: all executable codes
VALID_CODES = _FOSS_CODES.union(_PROPRIETARY_CODES, _DEFAULT_PROPRIETARY_CODES)


#: Configuration
_cfg = None


def cfg():
    """global configuration

    Returns:
        dict: configurated features
    """
    global _cfg
    return _cfg or _init()


def for_sim_type(sim_type):
    """Get cfg for simulation type

    Args:
        sim_type (str): srw, warppba, etc.

    Returns:
        dict: application specific config
    """
    import pykern.pkcollections

    c = cfg()
    return pykern.pkcollections.PKDict(
        c[sim_type] if sim_type in c else {}
    )


def _init():
    from pykern import pkconfig
    global _cfg

    def b(msg, dev=False):
        return (
            pkconfig.channel_in('dev') if dev else pkconfig.channel_in_internal_test(),
            bool,
            msg,
        )

    _cfg = pkconfig.init(
        # No secrets should be stored here (see sirepo.job.agent_env)
        api_modules=((), set, 'optional api modules, e.g. status'),
        default_proprietary_sim_types=(set(), set, 'codes where all users are authorized by default but that authorization can be revoked'),
        jspec=dict(
            derbenevskrinsky_force_formula=b('Include Derbenev-Skrinsky force formula'),
        ),
        proprietary_sim_types=(set(), set, 'codes that require authorization'),
        #TODO(robnagler) make this a sim_type config like srw and warpvnd
        rs4pi_dose_calc=(False, bool, 'run the real dose calculator'),
        sim_types=(set(), set, 'simulation types (codes) to be imported'),
        srw=dict(
            app_url=('/en/xray-beamlines.html', str, 'URL for SRW link'),
            beamline3d=b('Show 3D beamline plot'),
            hide_guest_warning=b('Hide the guest warning in the UI', dev=True),
            mask_in_toolbar=b('Show the mask element in toolbar'),
            show_open_shadow=(pkconfig.channel_in_internal_test(), bool, 'Show "Open as a New Shadow Simulation" menu item'),
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, 'Include 3D features in the Warp VND UI'),
            display_test_boxes=b('Display test boxes to visualize 3D -> 2D projections'),
        ),
    )
    i = _cfg.proprietary_sim_types.intersection(_cfg.default_proprietary_sim_types)
    assert not i, \
        f'{i}: cannot be in proprietary_sim_types and default_proprietary_sim_types'
    s = set(
        _cfg.sim_types or (
            _PROD_FOSS_CODES if pkconfig.channel_in('prod') else _FOSS_CODES
        )
    )
    s.update(_cfg.proprietary_sim_types, _cfg.default_proprietary_sim_types)
    for v in _DEPENDENT_CODES:
        if v[0] in s:
            s.add(v[1])
    x = s.difference(VALID_CODES)
    assert not x, \
        'sim_type(s) invalid={} expected={}'.format(x, VALID_CODES)
    _cfg.sim_types = frozenset(s)
    return _cfg
