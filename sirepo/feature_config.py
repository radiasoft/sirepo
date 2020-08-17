# -*- coding: utf-8 -*-
u"""List of features available

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# defer all imports so *_CODES is available to testing functions


#: Codes on beta and prod
_NON_ALPHA_FOSS_CODES = frozenset((
    'elegant',
    'jspec',
    'madx',
    'opal',
    'shadow',
    'srw',
    'synergia',
    'warppba',
    'warpvnd',
    'webcon',
    'zgoubi',
))

#: Codes on dev and alpha
_ALPHA_FOSS_CODES = frozenset((
    'irad',
    'ml',
    'myapp',
    'radia',
    'rcscon',
    'rs4pi',
))

#: All possible open source codes
_FOSS_CODES = _NON_ALPHA_FOSS_CODES.union(_ALPHA_FOSS_CODES)


#: codes for which we require dynamically loaded binaries
_PROPRIETARY_CODES = frozenset(('flash',))

#: all executable codes
VALID_CODES = _FOSS_CODES.union(_PROPRIETARY_CODES)


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
    if sim_type not in c:
        return pykern.pkcollections.PKDict()
    return pykern.pkcollections.PKDict(
        pykern.pkcollections.map_items(c[sim_type]),
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
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, 'Include 3D features in the Warp VND UI'),
            display_test_boxes=b('Display test boxes to visualize 3D -> 2D projections'),
        ),
    )
    s = set(
        _cfg.sim_types or (
            _FOSS_CODES if pkconfig.channel_in_internal_test() else _NON_ALPHA_FOSS_CODES
        )
    )
    s.update(_cfg.proprietary_sim_types)
    # jspec imports elegant, but elegant won't work if it is not a valid
    # sim_type so need to include here. Need a better model of
    # dependencies between codes.
    if 'jspec' in s and 'elegant' not in s:
        s.add('elegant')
    x = s.difference(VALID_CODES)
    assert not x, \
        'sim_type(s) invalid={} expected={}'.format(x, VALID_CODES)
    _cfg.sim_types = frozenset(s)
    return _cfg
