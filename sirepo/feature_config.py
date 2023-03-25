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
    ["omega", "madx"],
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
        "opal",
        "radia",
        "shadow",
        "srw",
        "synergia",
        "warppba",
        "warpvnd",
        "zgoubi",
    )
)

#: Codes on dev, alpha, and beta
_NON_PROD_FOSS_CODES = frozenset(
    (
        "myapp",
        "silas",
        "omega",
        "rshellweg",
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

    global _cfg

    def b(msg, dev=False):
        return (
            pkconfig.channel_in("dev") if dev else pkconfig.channel_in_internal_test(),
            bool,
            msg,
        )

    _cfg = pkconfig.init(
        # No secrets should be stored here (see sirepo.job.agent_env)
        api_modules=((), set, "optional api modules, e.g. status"),
        cloudmc=dict(
            data_storage_url=(
                "https://github.com/radiasoft/sirepo-data-cloudmc/raw/master/",
                str,
                "url base to reach cloudmc example h5m files",
            ),
        ),
        default_proprietary_sim_types=(
            frozenset(),
            set,
            "codes where all users are authorized by default but that authorization can be revoked",
        ),
        schema_common=dict(
            hide_guest_warning=b("Hide the guest warning in the UI", dev=True),
        ),
        jspec=dict(
            derbenevskrinsky_force_formula=b("Include Derbenev-Skrinsky force formula"),
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
        proprietary_sim_types=(
            frozenset(),
            set,
            "codes that contain proprietary information and authorization to use is granted manually",
        ),
        proprietary_oauth_sim_types=(
            frozenset(),
            set,
            "codes that contain proprietary information and authorization to use is granted through oauth",
        ),
        raydata=dict(
            file_reply_tmp_dir=pkconfig.RequiredUnlessDev(
                "raydata_file_reply_tmp_dir",
                _tmp_dir,
                "directory to share analysis pdfs between scan monitor and supervisor",
            ),
            scan_monitor_url=(
                "http://127.0.0.1:9001/scan-monitor",
                str,
                "url to reach scan monitor daemon",
            ),
        ),
        # TODO(pjm): myapp can't be in react_sim_types or unit tests fail
        react_sim_types=(
            ("jspec", "genesis", "warppba", "omega", "myapp")
            if pkconfig.channel_in("dev")
            else (),
            set,
            "React apps",
        ),
        sim_types=(set(), set, "simulation types (codes) to be imported"),
        slack_uri=(
            "https://slack.com/",
            str,
            "Link to Sirepo Slack workspace; uid will be appended",
        ),
        srw=dict(
            app_url=("/en/xray-beamlines.html", str, "URL for SRW link"),
            mask_in_toolbar=b("Show the mask element in toolbar"),
            show_video_links=(False, bool, "Display instruction video links"),
            show_open_shadow=(
                pkconfig.channel_in_internal_test(),
                bool,
                'Show "Open as a New Shadow Simulation" menu item',
            ),
            show_rsopt_ml=(
                pkconfig.channel_in_internal_test(),
                bool,
                'Show "Export ML Script" menu item',
            ),
        ),
        trust_sh_env=(
            False,
            bool,
            "Trust Bash env to run Python and agents",
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, "Include 3D features in the Warp VND UI"),
            display_test_boxes=b(
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


def _tmp_dir(dir):
    from pykern import pkconfig
    from pykern import pkio
    import os.path

    if pkconfig.channel_in("dev"):
        assert not os.path.isabs(dir), f"must use a relative path in dev dir={dir}"
        import sirepo.srdb

        return pkio.mkdir_parent(sirepo.srdb.root().join(dir))
    assert os.path.isabs(dir), f"must use an absolute path outside of dev dir={dir}"
    return pkio.py_path(dir)
