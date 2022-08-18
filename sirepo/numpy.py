# -*- coding: utf-8 -*-
"""Wrappers for numpy

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp
import numpy


def ndarray_from_ctx(file_ctx, skip_header, **kwargs):
    def _read():
        import csv
        import re

        with file_ctx as f:
            for r in csv.reader(f):
                yield ",".join(map(lambda v: re.sub(r'["\n\r,]', "", v), r))

    return numpy.genfromtxt(
        _read(), comments=None, delimiter=",", skip_header=skip_header, **kwargs
    )


def ndarray_from_csv(path, skip_header, **kwargs):
    return ndarray_from_ctx(open(path, "rt"), skip_header, **kwargs)
