# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import asks
from pykern.pkdebug import pkdp
import trio

def main():
    trio.run(_call_daemon)

async def _call_daemon():
    while True:
        try:
            response = await asks.get('http://localhost:8080')
            _process_response(response)
        except Exception as e:
            pkdp('Exception with _call_daemon(). Caused by: {}'.format(e))
        finally:
            await trio.sleep(1)

def _process_response(response):
    pkdp('Received response: {}'.format(response.content))
