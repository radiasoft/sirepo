# -*- coding: utf-8 -*-
u"""Wrappers for numpy

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import numpy as np

def ndarray_from_csv(path, skip_header, **kwargs):
    def _read():
        import csv
        import re

        with open(path, "rt") as f:
            for r in csv.reader(f):
                yield ','.join(map(lambda v: re.sub(r'["\n\r,]', '', v), r))
    return np.genfromtxt(
        _read(),
        comments=None,
        delimiter=',',
        skip_header=skip_header,
        **kwargs
    )
