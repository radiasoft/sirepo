# -*- coding: utf-8 -*-
"""Common functionality that is shared between the server, supervisor, and driver.

Because this is going to be shared across the server, supervisor, and driver it
must be py2 compatible.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


from pykern import pkconfig


job_supervisor_cfg = pkconfig.init(
    ip_address=('127.0.0.1', str, 'ip address the supervisor is listening to'),
    port=(8001, int, 'port the supervisor is listening to'),
)

server_cfg = pkconfig.init(
    supervisor_uri=(
        'http://{}:{}'.format(job_supervisor_cfg.ip_address, job_supervisor_cfg.port),
        str, 
        'uri to reach the supervisor'
        )
)

job_driver_cfg = pkconfig.init(
    supervisor_uri=(
        'http://{}:{}'.format(job_supervisor_cfg.ip_address, job_supervisor_cfg.port),
        str, 
        'uri to reach the supervisor'
        )
)
       

