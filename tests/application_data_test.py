# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_elegant(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    r = fc.sr_post(
        'getApplicationData',
        PKDict(
            simulationType='elegant',
            method='get_beam_input_type',
            input_file='bunchFile-sourceFile.forward-beam-output.sdds',
        ),
    )
    pkunit.pkre('elegant', r.input_type)


def test_srw_processed_image(fc):
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkfail
    from pykern import pkunit
    from sirepo import srunit

    r = fc.sr_sim_data('Sample from Image')
    r = fc.sr_post(
        'getApplicationData',
        {
            'simulationId': r.models.simulation.simulationId,
            'simulationType': fc.sr_sim_type,
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
