import pytest
import os
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import sirepo.uri


def test_favicon(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    import sirepo.resource
    import sys

    for a, p in PKDict(favicon="favicon.ico", faviconPng="favicon.png").items():
        r = fc.sr_get(a)
        with open(sirepo.resource.static("img", p), "rb") as f:
            s = f.read()
            pkeq(len(s), len(r.data))


def test_find_by_name(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq

    fc.sr_get(
        "findByName",
        PKDict(
            simulation_type="srw",
            application_mode="default",
            simulation_name="Undulator Radiation",
        ),
        redirect=False,
    ).assert_http_redirect("/srw#/findByName/default/Undulator%20Radiation")


def test_custom_errors(fc):
    from pykern.pkunit import pkre

    for k, v in simulation_db.SCHEMA_COMMON.customErrors.items():
        r = fc.sr_get(sirepo.uri.local_route(fc.sr_sim_type, v.route))
        r.assert_success()
        with open(sirepo.resource.static("html", v.url), "r") as f:
            s = f.read()
            pkre(v.msg, s)


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
        SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL="x@x.x",
    )


def test_jupyterhub_redirect(fc):
    fc.sr_get("redirectJupyterHub", redirect=False).assert_http_redirect("jupyterHub")


def test_simulation_redirect(fc):
    fc.sr_get("simulationRedirect", redirect=False).assert_http_redirect("simulations")


def test_check_auth_jupyterhub(fc):
    fc.sr_login_as_guest()
    # user doesn't exist
    fc.sr_get("checkAuthJupyterHub").assert_success()
    # user does exist
    fc.sr_get("checkAuthJupyterHub").assert_success()


def test_simulation_schema(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkexcept

    r = fc.sr_post_form(
        "simulationSchema",
        data=PKDict(simulationType=fc.sr_sim_type),
    )

    for k in ("model", "view"):
        assert k in r.keys()

    with pkexcept("unexpected status"):
        fc.sr_post_form(
            "simulationSchema",
            data=PKDict(simulationType="xyzzy"),
        )
