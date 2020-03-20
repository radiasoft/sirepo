# -*- coding: utf-8 -*-
u"""Wrappers for Tornado

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import asyncio
import tornado.queues


class Queue(tornado.queues.Queue):

    async def get(self):
        """Implements a cancellable Queue.get

        See https://github.com/radiasoft/sirepo/issues/2375
        """
        x = None
        try:
            x = super().get()
            return await x
        except asyncio.CancelledError:
            if x:
                try:
                    self.put_nowait(x.result())
                except Exception:
                    pass
            raise
