# -*- coding: utf-8 -*-
"""Constant values

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict

JSON_SUFFIX = ".json"

MPI_LOG = "mpi_run.log"

# POSIT: test ports do not collide with production ports when offset by this delta
PORT_DELTA_FOR_TEST = 100

PORT_MAX = 32767
PORT_MIN = 1025

PORT_DEFAULTS = PKDict(
    http=8000,
    jupyterhub=8002,
    nginx_proxy=8080,
    react=3000,
    supervisor=8001,
    uwsgi=8000,
)
