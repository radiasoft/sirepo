# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.rftrack`

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_generate_python():
    from pykern import pkio, pkunit

    with pkunit.save_chdir_work():
        from sirepo.template import rftrack

        data = _example_data()
        actual = rftrack.python_source_for_model(data, model=None, qcall=None)
        pkio.write_text("parameters.py", actual)


def test_track_drift_and_screen():
    import subprocess
    import sys
    from pykern import pkio, pkunit

    with pkunit.save_chdir_work():
        from sirepo.template import rftrack
        import numpy

        data = _example_data()
        pkio.write_text(
            "parameters.py",
            rftrack.python_source_for_model(data, model=None, qcall=None),
        )
        subprocess.check_call([sys.executable, "parameters.py"])
        pkunit.pkok(
            pkio.py_path("initial_particles.npy").exists(),
            "missing initial_particles.npy",
        )
        pkunit.pkok(pkio.py_path("stats.npy").exists(), "missing stats.npy")
        pkunit.pkok(
            pkio.py_path("final_particles.npy").exists(),
            "missing final_particles.npy",
        )
        pkunit.pkok(pkio.py_path("screen-0.npy").exists(), "missing screen-0.npy")
        t = numpy.load("stats.npy")
        pkunit.pkeq(True, len(t) > 0)
        p = numpy.load("final_particles.npy")
        pkunit.pkeq(100, len(p))


def _example_data(
    elements=None, beamline_items=None, beam=None, simulation_settings=None
):
    import sirepo.sim_data
    from pykern.pkcollections import PKDict

    els = elements or [
        PKDict(_id=2, type="DRIFT", name="D1", l=1.0),
        PKDict(_id=3, type="SCREEN", name="S1", l=0),
    ]
    items = beamline_items or [e._id for e in els]
    # beamline.positions[idx].elemedge is the absolute z position of
    # items[idx]; default to sequential (cumulative length) placement,
    # matching what the lattice editor's "absolute" positioning mode would
    # have computed for a simple non-overlapping lattice.
    by_id = {e._id: e for e in els}
    positions = []
    edge = 0.0
    for item_id in items:
        positions.append(PKDict(elemedge=edge))
        edge += by_id[abs(item_id)].get("l", 0)

    data = PKDict(
        report="animation",
        simulationType="rftrack",
        models=PKDict(
            beam=PKDict(
                particle="electron",
                mass=0.51099895,
                charge=-1,
                pc=100.0,
                charge_nC=1.0,
                np=100,
                emit_x=1.0,
                emit_y=1.0,
                beta_x=1.0,
                beta_y=1.0,
                alpha_x=0.0,
                alpha_y=0.0,
                sigma_t=1.0,
                sigma_pt=1.0,
            ).pkupdate(beam or PKDict()),
            beamlines=[
                PKDict(id=1, name="BL1", items=items, positions=positions),
            ],
            commands=[],
            elements=els,
            simulation=PKDict(
                visualizationBeamlineId=1,
                elementPosition="absolute",
            ),
            simulationSettings=PKDict(
                spaceCharge="none",
            ).pkupdate(simulation_settings or PKDict()),
        ),
    )
    sirepo.sim_data.get_class("rftrack").fixup_old_data(data, qcall=None)
    return data
