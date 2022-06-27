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
PROD_FOSS_CODES = frozenset((
    'controls',
    'elegant',
    'genesis',
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
    'zgoubi',
))

#: Codes on dev, alpha, and beta
_NON_PROD_FOSS_CODES = frozenset((
    'irad',
    'myapp',
    'cloudmc',
    'rcscon',
    'rs4pi',
    'silas',
))

#: All possible open source codes
FOSS_CODES = PROD_FOSS_CODES.union(_NON_PROD_FOSS_CODES)

#: Configuration
_cfg = None


def auth_controlled_sim_types():
    """All sim types that require granted authentication to access

    Returns:
      frozenset:  enabled sim types that require role
    """
    return frozenset(
        cfg().moderated_sim_types.union(
            cfg().proprietary_sim_types,
            cfg().proprietary_oauth_sim_types,
        ),
    )


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
    ).pkupdate(c.schema_common)


def proprietary_sim_types():
    """All sim types that have proprietary information and require granted access to use

    Granted access can be through oauth or manual management of the role

    Returns:
      frozenset:  enabled sim types that require role
    """
    return frozenset(
        cfg().proprietary_sim_types.union(cfg().proprietary_oauth_sim_types),
    )


def _data_dir(value):
    import sirepo.srdb
    return sirepo.srdb.root().join(value)


def _init():
    from pykern import pkconfig
    from pykern import pkio
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
        schema_common=dict(
            hide_guest_warning=b('Hide the guest warning in the UI', dev=True),
        ),
        moderated_sim_types=(frozenset(), set, 'codes where all users must be authorized via moderation'),
        jspec=dict(
            derbenevskrinsky_force_formula=b('Include Derbenev-Skrinsky force formula'),
        ),
        package_path=(
            tuple(['sirepo']),
            tuple,
            'Names of root packages that should be checked for codes and resources. Order is important, the first package with a matching code/resource will be used. sirepo added automatically.',
        ),
        proprietary_sim_types=(
            frozenset(),
            set,
            'codes that contain proprietary information and authorization to use is granted manually',
        ),
        proprietary_oauth_sim_types=(
            frozenset(),
            set,
            'codes that contain proprietary information and authorization to use is granted through oauth',
        ),
        raydata=dict(
            data_dir=(None, _data_dir, 'abspath of dir to store raydata analysis output'),
        ),
        sim_types=(set(), set, 'simulation types (codes) to be imported'),
        slack_uri=('https://slack.com/', str, 'Link to Sirepo Slack workspace; uid will be appended'),
        srw=dict(
            app_url=('/en/xray-beamlines.html', str, 'URL for SRW link'),
            mask_in_toolbar=b('Show the mask element in toolbar'),
            show_video_links=(False, bool, 'Display instruction video links'),
            show_open_shadow=(pkconfig.channel_in_internal_test(), bool, 'Show "Open as a New Shadow Simulation" menu item'),
            show_rsopt_ml=(pkconfig.channel_in_internal_test(), bool, 'Show "Export ML Script" menu item'),
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, 'Include 3D features in the Warp VND UI'),
            display_test_boxes=b('Display test boxes to visualize 3D -> 2D projections'),
        ),
    )
    s = set(
        _cfg.sim_types or (
            PROD_FOSS_CODES if pkconfig.channel_in('prod') else FOSS_CODES
        )
    )
    s.update(
        _cfg.moderated_sim_types,
        _cfg.proprietary_sim_types,
        _cfg.proprietary_oauth_sim_types,
    )
    for v in _DEPENDENT_CODES:
        if v[0] in s:
            s.add(v[1])
    _cfg.sim_types = frozenset(s)
    if 'raydata' in _cfg.sim_types:
        assert _cfg.raydata.data_dir, \
            'raydata is a sim type but no cfg.raydata.data_dir (also check job_driver.cfg.aux_volumes)'
    _check_packages(_cfg.package_path)
    return _cfg


def _check_packages(packages):
    import importlib
    for p in packages:
        importlib.import_module(p)
