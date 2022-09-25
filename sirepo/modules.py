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

    sirepo.flask

    # auth needs init these first, no imports
    sirepo.cookie.init()
    sirepo.auth_db.init()


    # these can be first
    sirepo.http_request (
        simulation_db
    )
    sirepo.http_reply.init(
        simulation_db
    )
    sirepo.uri.init(
        simulation_db=m.simulation_db,
        uri_router=m
    )
    # quest
    sirepo.quest.init(
        http_reply
        http_request
        uri_router
    )

    sirepo.uri_router.init_module(app, simulation_db)

    # after auth_db
    sirepo.session.init()


    # job_supervisor doesn't need job_driver in its init so do first
    sirepo.job_supervisor.init_module(job_driver)
    sirepo.job_driver.init_module(sirepo.job_supervisor)


./uri_router.py:def init_module(app, simulation_db):
./job_driver/__init__.py:def init_module(job_supervisor_module):
./srtime.py:def init_module():
./auth_db.py:def init_module():
./session.py:def init_module():
./job_supervisor.py:def init_module():
./job.py:def init_module():
./http_request.py:def init_module(**imports):
./uri.py:def init_module(**imports):
./http_reply.py:def init_module(**imports):
./cookie.py:def init_module():
./flask.py:def init_module(_in_app=True):
./auth/__init__.py:def init_module():
./quest.py:def init_module(**imports):
