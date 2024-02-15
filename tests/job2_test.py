# -*- coding: utf-8 -*-
"""Test statelessCompute, statefulCompute, analysisJob

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_elegant(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkdebug
    from sirepo.template import lattice

    def _do_backtracking(fc):
        t = "elegant"
        d = fc.sr_sim_data(sim_name="Backtracking", sim_type=t)
        return d, _do(
            fc,
            "statefulCompute",
            method="get_beam_input_type",
            simulationId=d.models.simulation.simulationId,
            simulationType=t,
            args=PKDict(input_file=None),
        )

    d, r = _do_backtracking(fc)
    _completed(r)
    _completed(fc.sr_run_sim(d, "animation"))
    _completed(_do_analysis_job(fc, "log_to_html", "animation", d))


def test_madx(fc):
    from pykern import pkunit, pkdebug
    from pykern.pkcollections import PKDict

    def _do_fodo_ptc(fc, method):
        t = "madx"
        d = fc.sr_sim_data(sim_name="FODO PTC", sim_type=t)
        return _do(
            fc,
            "statelessCompute",
            method,
            simulationId=d.models.simulation.simulationId,
            simulationType=t,
            args=PKDict(
                bunch=d.models.bunch,
                command_beam=d.models.command_beam,
                variables=d.models.rpnVariables,
            ),
        )

    r = _do_fodo_ptc(fc, "calculate_bunch_parameters")
    pkunit.pkok(r.get("command_beam"), "response={}", r)
    # must be pretty specific. If it contains a "-", it will be caught by split_jid.
    # If it doesn't have a valid file name character, it'll be caught by assert_sim_db_file_path.
    # This method is illegal and makes it through.
    r = _do_fodo_ptc(fc, "0x23")
    pkunit.pkre("method=.*invalid", r.error)


def _do(fc, api, method, **kwargs):
    from pykern.pkcollections import PKDict

    return fc.sr_post(api, PKDict(method=method, **kwargs))


def _do_analysis_job(fc, method, model, data):
    from pykern.pkcollections import PKDict

    return _do(
        fc,
        "analysisJob",
        method,
        computeModel=model,
        simulationId=data.models.simulation.simulationId,
        simulationType=data.simulationType,
    )


def _completed(resp):
    from pykern import pkunit

    pkunit.pkeq("completed", resp.state, "aeresponse={}", resp)
