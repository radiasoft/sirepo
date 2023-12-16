# -*- coding: utf-8 -*-
"""Stateful compute test

:copyright: Copyright (c) 2022-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


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
