# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.srw`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkunit import pkeq, pkok

_N_BINS = 100


def setup_module(module):
    import os

    # Set max to something reasonable for testing
    os.environ.update(
        SIREPO_JOB_MAX_MESSAGE_BYTES=str(_N_BINS * _N_BINS),
    )


def test_srw_resize_3d(fc):
    from sirepo.template import srw
    import numpy

    a, xr, yr = srw._reshape_3d(
        numpy.random.rand(srw._MAX_MESSAGE_BYTES),
        [0, 0, 0, 0.0, 1.0, _N_BINS, 0.0, 1.0, _N_BINS],
        PKDict(),
    )
    pkok(
        xr[2] < _N_BINS and yr[2] < _N_BINS,
        "did not reduce bins nx={} ny={}",
        xr[2],
        yr[2],
    )
