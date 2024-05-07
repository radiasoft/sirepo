"""Test global resources system

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_PUBLIC_PORT = 12666


def setup_module(_):
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_ENABLE_GLOBAL_RESOURCES="1",
        SIREPO_GLOBAL_RESOURCES_PUBLIC_PORTS_MAX=f"{_PUBLIC_PORT + 1}",
        SIREPO_GLOBAL_RESOURCES_PUBLIC_PORTS_MIN=f"{_PUBLIC_PORT}",
    )


def test_global_resources(fc):
    from pykern.pkunit import pkeq, pkok

    d = fc.sr_sim_data()
    a = _post(fc, "globalResources", d)
    pkeq(["public_port"], list(a.keys()))
    pkeq(_PUBLIC_PORT, a.public_port)
    b = _post(fc, "globalResources", d)
    pkeq(a, b)
    c = _post(fc, "statelessCompute", d, method="global_resources")
    pkeq(a.public_port, c.public_port)
    e = {"public_port", "ip", "ports"}
    a = set(c.keys())
    pkok(e.issubset(a), "epect={} subset of actual={}", e, a)


def _post(fc, api, sim_data, **kwargs):
    from pykern.pkcollections import PKDict

    return fc.sr_post(
        api,
        PKDict(
            simulationId=sim_data.models.simulation.simulationId,
            simulationType=sim_data.simulationType,
            **kwargs,
        ),
    )
