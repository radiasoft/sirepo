# -*- coding: utf-8 -*-
"""Wrappers for numpy

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import numpy


def ndarray_from_generator(generator, skip_header, **kwargs):
    return numpy.genfromtxt(
        generator, comments=None, delimiter=",", skip_header=skip_header, **kwargs
    )


def ndarray_from_csv(path, skip_header, **kwargs):
    return ndarray_from_generator(open(path, "rt"), skip_header, **kwargs)
