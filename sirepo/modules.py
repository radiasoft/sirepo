# -*- coding: utf-8 -*-
"""initialize modules based on mode

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkinspect


def import_and_init(name):
    n = pykern.pkinspect.caller_module().__name__
    if n == "sirepo.job_supervisor":
        pass
    elif n == "sirepo.server":
        pass
    elif n = "sirepo.auth":
        pass
    elif n = "sirepo.uri":
        # just needs itself
        pass
    else:
        raise AssertionError(f"unsupported module={n}")


    sirepo.auth_db.init_module()



    sirepo.srtime.init_module()

    sirepo.uri_router.init_module(app, simulation_db)

    sirepo.http_request.init(
        simulation_db=simulation_db,
    )
    sirepo.http_reply.init(
        simulation_db=simulation_db,
    )
    sirepo.uri.init(
        simulation_db=simulation_db,
        uri_router=pkinspect.this_module(),
    )
    sirepo.quest.init(
        http_reply=sirepo.http_reply,
        http_request=sirepo.http_request,
        uri_router=pkinspect.this_module(),
    )

    # after auth_db
    sirepo.session.init()

    job_driver.init_module(sirepo.job_supervisor)

    sirepo.job_supervisor.init_module(job_driver=)
