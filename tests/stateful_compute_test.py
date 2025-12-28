"""Stateful compute test

:copyright: Copyright (c) 2022-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_srw_sample_preview(fc):
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkfail
    from pykern import pkunit
    from sirepo import srunit
    from PIL import Image

    r = fc.sr_sim_data("Sample from Image")
    r = fc.sr_post(
        "statefulCompute",
        {
            "simulationId": r.models.simulation.simulationId,
            "simulationType": fc.sr_sim_type,
            "method": "sample_preview",
            "baseImage": "sample.tif",
            "model": {
                "areaXEnd": 1280,
                "areaXStart": 0,
                "areaYEnd": 834,
                "areaYStart": 0,
                "backgroundColor": 0,
                "cropArea": "1",
                "cutoffBackgroundNoise": 0.5,
                "invert": "0",
                "outputImageFormat": "tif",
                "rotateAngle": 0,
                "rotateReshape": "0",
                "sampleSource": "file",
                "shiftX": 0,
                "shiftY": 0,
                "tileColumns": 1,
                "tileImage": "0",
                "tileRows": 1,
            },
        },
        raw_response=True,
    )
    p = str(pkunit.work_dir().join("x.tif"))
    d = r.assert_success()
    with open(p, "wb") as f:
        f.write(d)
    # Validate image
    Image.open(p)


def test_srw_model_list(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern import pkunit
    from sirepo import srunit

    d = fc.sr_sim_data("Young's Double Slit Experiment")
    fc.sr_post(
        "listSimulations",
        PKDict(simulationType=fc.sr_sim_type),
    )
    r = fc.sr_post(
        "statefulCompute",
        PKDict(
            method="model_list",
            simulationType=fc.sr_sim_type,
            args=PKDict(model_name="electronBeam"),
        ),
    )
    pkunit.pkok(
        not r.get("error") or r.get("state", "ok") == "ok",
        "error in reply={}",
        r,
    )
    pkunit.pkok(isinstance(r.get("modelList"), list), "model_list not in reply={}", r)
    r = fc.sr_post(
        "newSimulation",
        PKDict(
            name="howdy",
            folder="/",
            simulationType=fc.sr_sim_type,
            sourceType=d.models.simulation.sourceType,
        ),
    )
    d.models.electronBeam.pkupdate(name="xyzzy", isReadOnly=False)
    d.models.simulation = r.models.simulation
    fc.sr_post("saveSimulationData", d)
    r = fc.sr_post(
        "statefulCompute",
        PKDict(
            method="model_list",
            simulationType=fc.sr_sim_type,
            args=PKDict(model_name="electronBeam"),
        ),
    )
    m = next(filter(lambda x: x.name == "xyzzy", r.modelList))
    pkunit.pkok(m, "user model not in reply={}", r)
    r = fc.sr_post(
        "statefulCompute",
        PKDict(
            method="delete_user_models",
            simulationType=fc.sr_sim_type,
            args=PKDict(electron_beam=m),
        ),
    )
    pkunit.pkeq("completed", r.state)
    r = fc.sr_post(
        "statefulCompute",
        PKDict(
            method="model_list",
            simulationType=fc.sr_sim_type,
            args=PKDict(model_name="electronBeam"),
        ),
    )
    pkunit.pkok(
        not any(filter(lambda x: x.name == "xyzzy", r.modelList)),
        "user model in reply={}",
        r,
    )
