"""List of features available

To add a code that is not in the default list:

    export SIREPO_FEATURE_CONFIG_SIM_TYPES=raydata:DEFAULT

:copyright: Copyright (c) 2016-2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# defer all imports so *_CODES is available to testing functions


#: Codes that depend on other codes
_DEPENDENT_CODES = dict(
    jspec=frozenset(("elegant",)),
    controls=frozenset(("madx",)),
    omega=frozenset(("elegant", "omega", "genesis")),
)

FOSS_CODES = frozenset(
    (
        "activait",
        "canvas",
        "controls",
        "cortex",
        "elegant",
        "epicsllrf",
        "genesis",
        "hellweg",
        "impactt",
        "impactx",
        "jspec",
        "madx",
        "myapp",
        "omega",
        "opal",
        "openmc",
        "radia",
        "shadow",
        "silas",
        "srw",
        "warppba",
        "warpvnd",
        "zgoubi",
    )
)

_ALL_CODES = "DEFAULT"

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


def have_payments():
    return "payments" in cfg().api_modules


def proprietary_sim_types():
    """All sim types that have proprietary information and require granted access to use

    Granted access can be through oauth or manual management of the role

    Returns:
      frozenset:  enabled sim types that require role
    """
    return frozenset(
        cfg().proprietary_sim_types.union(cfg().proprietary_oauth_sim_types),
    )


def _init():
    from pykern import pkconfig
    from pykern import pkio
    from pykern.pkdebug import pkdp
    from sirepo import const

    global _cfg

    def _check_package_path(path):
        import importlib

        for p in path:
            importlib.import_module(p)

    def _default_sim_types(sim_types):
        if not sim_types or _ALL_CODES in sim_types:
            sim_types.update(FOSS_CODES)
            sim_types.discard(_ALL_CODES)
        return sim_types

    def _dev(msg):
        return (pkconfig.in_dev_mode(), bool, msg)

    def _is_fedora_36():
        from pykern import pkio

        p = pkio.py_path("/etc/os-release")
        if not p.check():
            return False
        return "fedora:36" in p.read()

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
        is_registration_moderated=(
            False,
            bool,
            "moderation required before adding role 'user'",
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
        openmc=dict(
            data_storage_url=(
                "https://github.com/radiasoft/sirepo-data-cloudmc/raw/master/",
                str,
                "url base to reach openmc example h5m files",
            ),
            # TODO(pjm): remove this when FreeCAD is available in sirepo container
            has_freecad=_dev("FreeCAD library available"),
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
            scan_monitor_api_secret=(
                "a_secret",
                str,
                "secret to secure communication with scan monitor",
            ),
            scan_monitor_url=(
                "http://127.0.0.1:9001/scan-monitor",
                str,
                "url to reach scan monitor daemon",
            ),
        ),
        schema_common=dict(
            support_email=(
                "support@sirepo.com",
                str,
                "Support email address",
            ),
        ),
        sim_types=(set(), set, "simulation types (codes) to be imported"),
        srw=dict(
            app_url=("/en/xray-beamlines.html", str, "URL for SRW link"),
            mask_in_toolbar=_test("Show the mask element in toolbar"),
            show_video_links=(False, bool, "Display instruction video links"),
            show_open_shadow=_test('Show "Open as a New Shadow Simulation" menu item'),
            show_rsopt_ml=_test('Show "Export ML Script" menu item'),
        ),
        trial_expiration_days=(
            30,
            pkconfig.parse_positive_int,
            "number of days a sirepo trial is active",
        ),
        trust_sh_env=(
            False,
            bool,
            "Trust Bash env to run Python and agents",
        ),
        ui_websocket=(
            True,
            bool,
            "whether the UI should use a websocket",
        ),
        vue_sim_types=(
            ("cortex",),
            set,
            "Vue apps",
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, "Include 3D features in the Warp VND UI"),
            display_test_boxes=_dev(
                "Display test boxes to visualize 3D -> 2D projections"
            ),
        ),
    )
    s = _default_sim_types(set(_cfg.sim_types))
    s.update(
        _cfg.default_proprietary_sim_types,
        _cfg.moderated_sim_types,
        _cfg.proprietary_oauth_sim_types,
        _cfg.proprietary_sim_types,
    )
    for k, v in _DEPENDENT_CODES.items():
        if k in s:
            s.update(v)
    _cfg.sim_types = frozenset(s)
    _check_package_path(_cfg.package_path)
    _cfg.is_fedora_36 = _is_fedora_36()
    return _cfg
