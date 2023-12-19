# -*- coding: utf-8 -*-
"""Test statelessCompute API

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_elegant_get_beam_input_type(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    f = None
    r = _do_stateful_compute(fc, "get_beam_input_type", PKDict(input_file=f))
    pkunit.pkeq(None, f)


def test_invalid_method(fc):
    from pykern import pkunit, pkdebug

    # must be pretty specific. If it contains a "-", it will be caught by split_jid.
    # If it doesn't have a valid file name character, it'll be caught by assert_sim_db_file_path.
    # This method is illegal and makes it through.
    m = "0x23"
    r = _do_stateless_compute(fc, m)
    pkunit.pkre(f"method={m}.*invalid", r.error)


def test_madx_calculate_bunch_parameters(fc):
    from pykern import pkunit, pkdebug

    r = _do_stateless_compute(fc, "calculate_bunch_parameters")
    pkdebug.pkdp(r)
    pkunit.pkok(r.get("command_beam"), "unexpected response={}", r)


def _do(fc, api, method, data):
    from pykern.pkcollections import PKDict

    return fc.sr_post(
        api,
        PKDict(
            method=method,
            args=data,
            simulationId=data.simulationId,
            simulationType=data.simulationType,
        ),
    )


def _do_stateful_compute(fc, method, data):
    from pykern.pkcollections import PKDict

    t = "elegant"
    d = fc.sr_sim_data(sim_name="Backtracking", sim_type=t)
    return _do(
        fc,
        "statefulCompute",
        method,
        PKDict(simulationId=d.models.simulation.simulationId, simulationType=t, **data),
    )


def _do_stateless_compute(fc, method, data=None):
    from pykern.pkcollections import PKDict

    data = data or PKDict()
    t = "madx"
    d = fc.sr_sim_data(sim_name="FODO PTC", sim_type=t)
    return _do(
        fc,
        "statelessCompute",
        method,
        PKDict(
            bunch=d.models.bunch,
            command_beam=d.models.command_beam,
            simulationId=d.models.simulation.simulationId,
            simulationType=t,
            variables=d.models.rpnVariables,
            **data,
        ),
    )
