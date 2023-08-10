# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.srw`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkunit import pkeq, pkok

_N_BINS = 100


def setup_module(module):
    from pykern import pkconfig
    pkconfig.reset_state_for_testing(
        dict(
            SIREPO_JOB_MAX_MESSAGE_BYTES=str(_N_BINS * _N_BINS),
        )
    )


def test_srw_resize_3d():
    from sirepo import job
    from sirepo.template import srw
    import numpy

    a, xr, yr = srw._reshape_3d(
        numpy.random.rand(job.cfg().max_message_bytes),
        [0, 0, 0, 0.0, 1.0, _N_BINS, 0.0, 1.0, _N_BINS],
        PKDict(),
    )
    pkok(
        xr[2] < _N_BINS,
        "did not reduce bins nx={}",
        xr[2],
    )
    pkok(
        yr[2] < _N_BINS,
        "did not reduce bins ny={}",
        yr[2],
    )
