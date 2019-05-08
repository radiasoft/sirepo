# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

def test_processed_image():
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkfail
    from pykern import pkunit
    from sirepo import srunit

    sim_type = 'srw'
    fc = srunit.flask_client(sim_types=sim_type)
    fc.sr_login_as_guest(sim_type)
    r = fc.sr_sim_data(sim_type, 'Sample from Image')
    r = fc.sr_post(
        'getApplicationData',
        {
            'simulationId': r.models.simulation.simulationId,
            'simulationType': sim_type,
            'method': 'processedImage',
            'baseImage': 'sample.tif',
            'model': {
                'cutoffBackgroundNoise': 0.5,
                'backgroundColor': 0,
                'rotateAngle': 0,
                'rotateReshape': '0',
                'cropArea': '1',
                'areaXStart': 0,
                'areaXEnd': 1280,
                'areaYStart': 0,
                'areaYEnd': 834,
                'shiftX': 0,
                'shiftY': 0,
                'invert': '0',
                'tileImage': '0',
                'tileRows': 1,
                'tileColumns': 1,
                'outputImageFormat': 'tif',
            }
        },
        {
            'filename': 'foo.tif',
        },
        raw_response=True,
    )
    with open(str(pkunit.work_dir().join('x.tif')), 'wb') as f:
        f.write(r.data)
