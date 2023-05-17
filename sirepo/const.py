# -*- coding: utf-8 -*-
"""Constant values

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import asyncio
from pykern.pkcollections import PKDict

ASYNC_CANCELED_ERROR = asyncio.CancelledError

STATIC_D = "static"

JSON_SUFFIX = ".json"

MPI_LOG = "mpi_run.log"

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

TEST_PORT_RANGE = range(10000, 11000)

SRUNIT_USER_AGENT = "srunit/1.0"
