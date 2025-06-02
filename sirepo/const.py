"""Constant values

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import asyncio
from pykern.pkcollections import PKDict

ASYNC_CANCELED_ERROR = asyncio.CancelledError

STATIC_D = "static"

JSON_SUFFIX = ".json"

#: where template resources and template non-sim user files live
LIB_DIR = "lib"

LOCALHOST_FQDN = "localhost.localdomain"

# matches requirements for uid and isn't actually put in the db
MOCK_UID = "someuser"

MPI_LOG = "mpi_run.log"

PORT_MAX = 32767
PORT_MIN = 1025

PORT_DEFAULTS = PKDict(
    http=8000,
    jupyterhub=8002,
    nginx_proxy=8080,
    supervisor=8001,
    vue=8008,
)

#: These values will be injected into simulation_db.SCHEMA_COMMON
SCHEMA_COMMON = PKDict(
    websocketMsg=PKDict(
        kind=PKDict(
            httpRequest=1,
            httpReply=2,
            srException=3,
            asyncMsg=4,
        ),
        method=PKDict(
            setCookies="setCookies",
        ),
        version=1,
    ),
)

#: Simulation file name saved both in sim db and run directory
SIM_DATA_BASENAME = "sirepo-data" + JSON_SUFFIX

#: Simulation file name saved both in sim db and run directory
SIM_RUN_INPUT_BASENAME = "in" + JSON_SUFFIX

SIM_TYPE_JUPYTERHUBLOGIN = "jupyterhublogin"

SRUNIT_USER_AGENT = "srunit/1.0"

TEST_PORT_RANGE = range(10000, 20000)

#: hardwired root of development src tree; Not a py.path, because must defer tilde evaluation
DEV_SRC_RADIASOFT_DIR = "~/src/radiasoft/"
