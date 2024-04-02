# -*- coding: utf-8 -*-
"""List of features available

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
# defer all imports so *_CODES is available to testing functions


#: Codes that depend on other codes. [x][0] depends on [x][1]

_DEPENDENT_CODES = [
    ["jspec", "elegant"],
    ["controls", "madx"],
    ["omega", "elegant"],
    ["omega", "genesis"],
    ["omega", "opal"],
]

#: Codes on prod
PROD_FOSS_CODES = frozenset(
    (
        "activait",
        "cloudmc",
        "controls",
        "elegant",
        "genesis",
        "jspec",
        "madx",
        "omega",
        "opal",
        "radia",
        "shadow",
        "silas",
        "srw",
        "warppba",
        "warpvnd",
        "zgoubi",
    )
)

#: Codes on dev, alpha, and beta
_NON_PROD_FOSS_CODES = frozenset(
    (
        "epicsllrf",
        "myapp",
        "hellweg",
    )
)

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
            cfg().default_proprietary_sim_types,
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
    return pykern.pkcollections.PKDict(c[sim_type] if sim_type in c else {}).pkupdate(
        c.schema_common
    )


def proprietary_sim_types():
    """All sim types that have proprietary information and require granted access to use

    Granted access can be through oauth or manual management of the role

    Returns:
      frozenset:  enabled sim types that require role
    """
    return frozenset(
        cfg().proprietary_sim_types.union(cfg().proprietary_oauth_sim_types),
    )


def _is_fedora_36():
    from pykern import pkio

    p = pkio.py_path("/etc/os-release")
    if not p.check():
        return False
    return "fedora:36" in p.read()


def _init():
    from pykern import pkconfig
    from pykern import pkio
    from pykern.pkdebug import pkdp

    global _cfg

    def _dev(msg):
        return (pkconfig.in_dev_mode(), bool, msg)

    def _test(msg):
        return (pkconfig.channel_in_internal_test(), bool, msg)

    _cfg = pkconfig.init(
        # No secrets should be stored here (see sirepo.job.agent_env)
        api_modules=((), set, "optional api modules, e.g. status"),
        activait=dict(
            data_storage_url=(
                "https://github.com/radiasoft/sirepo-data-activait/raw/master/",
                str,
                "url base to reach activait example files",
            ),
        ),
        cloudmc=dict(
            data_storage_url=(
                "https://github.com/radiasoft/sirepo-data-cloudmc/raw/master/",
                str,
                "url base to reach cloudmc example h5m files",
            ),
        ),
        debug_mode=(pkconfig.in_dev_mode(), bool, "control debugging output"),
        default_proprietary_sim_types=(
            frozenset(),
            set,
            "codes where all users are authorized by default but that authorization can be revoked",
        ),
        enable_global_resources=(
            False,
            bool,
            "enable the global resources allocation system",
        ),
        jspec=dict(
            derbenevskrinsky_force_formula=_test(
                "Include Derbenev-Skrinsky force formula"
            ),
        ),
        moderated_sim_types=(
            frozenset(),
            set,
            "codes where all users must be authorized via moderation",
        ),
        package_path=(
            tuple(["sirepo"]),
            tuple,
            "Names of root packages that should be checked for codes and resources. Order is important, the first package with a matching code/resource will be used. sirepo added automatically.",
        ),
        proprietary_oauth_sim_types=(
            frozenset(),
            set,
            "codes that contain proprietary information and authorization to use is granted through oauth",
        ),
        proprietary_sim_types=(
            frozenset(),
            set,
            "codes that contain proprietary information and authorization to use is granted manually",
        ),
        raydata=dict(
            scan_monitor_url=(
                "http://127.0.0.1:9001/scan-monitor",
                str,
                "url to reach scan monitor daemon",
            ),
        ),
        schema_common=dict(
            hide_guest_warning=_dev("Hide the guest warning in the UI"),
        ),
        sim_types=(set(), set, "simulation types (codes) to be imported"),
        slack_uri=(
            "https://slack.com/",
            str,
            "Link to Sirepo Slack workspace; uid will be appended",
        ),
        srw=dict(
            app_url=("/en/xray-beamlines.html", str, "URL for SRW link"),
            mask_in_toolbar=_test("Show the mask element in toolbar"),
            show_video_links=(False, bool, "Display instruction video links"),
            show_open_shadow=_test('Show "Open as a New Shadow Simulation" menu item'),
            show_rsopt_ml=_test('Show "Export ML Script" menu item'),
        ),
        trust_sh_env=(
            False,
            bool,
            "Trust Bash env to run Python and agents",
        ),
        ui_websocket=(
            pkconfig.in_dev_mode(),
            bool,
            "whether the UI should use a websocket",
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, "Include 3D features in the Warp VND UI"),
            display_test_boxes=_dev(
                "Display test boxes to visualize 3D -> 2D projections"
            ),
        ),
    )
    s = set(
        _cfg.sim_types
        or (PROD_FOSS_CODES if pkconfig.channel_in("prod") else FOSS_CODES)
    )
    s.update(
        _cfg.default_proprietary_sim_types,
        _cfg.moderated_sim_types,
        _cfg.proprietary_oauth_sim_types,
        _cfg.proprietary_sim_types,
    )
    for v in _DEPENDENT_CODES:
        if v[0] in s:
            s.add(v[1])
    _cfg.sim_types = frozenset(s)
    _check_packages(_cfg.package_path)
    _cfg.is_fedora_36 = _is_fedora_36()
    return _cfg


def _check_packages(packages):
    import importlib

    for p in packages:
        importlib.import_module(p)
