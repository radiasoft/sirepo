# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.srw`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
from pykern.pkcollections import PKDict


def test_srw_resize_3d(fc):
    from sirepo.template import srw
    from pykern.pkdebug import pkdlog
    import numpy
    import os

    env = PKDict(os.environ)
    cfg = PKDict(
        SIREPO_JOB_MAX_MESSAGE_BYTES="1e4",
    )
    env.pkupdate(**cfg)
    pkdlog("MaX B {}", srw._MAX_MESSAGE_BYTES)
    assert 0

    #a = numpy.random.rand(srw._MAX_MESSAGE_BYTES)
    #r = PKDict()
    #srw._reshape_3d(a, [], r)


