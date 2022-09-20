# -*- coding: utf-8 -*-
"""Constant values

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict

JSON_SUFFIX = ".json"

MPI_LOG = "mpi_run.log"

PORT_DEFAULTS = PKDict(
    http=8000,
    jupyterhub=8002,
    nginx_proxy=8080,
    react=1025,
    supervisor=8001,
    uwsgi=8000,
)

# POSIT: test ports do not collide with production ports when offset by this delta
PORT_DELTA_FOR_TEST = 1
