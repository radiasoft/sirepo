# -*- coding: utf-8 -*-
u"""Wrappers for Tornado

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdlog, pkdexc
import sirepo.util
import tornado.queues


class Queue(tornado.queues.Queue):

    async def get(self):
        """Implements a cancelable Queue.get

        See https://github.com/radiasoft/sirepo/issues/2375
        """
        x = None
        try:
            # this returns a future, which may get a result
            # before the await returns, that is, if the task
            # is canceled after another task has put something
            # on the queue and before this task finishes the await.
            x = super().get()
            return await x
        except sirepo.util.ASYNC_CANCELED_ERROR:
            if x:
                try:
                    r = x.result()
                except Exception:
                    # there are many exceptions that can happen,
                    # including throwing an exception on the Future.
                    # However, none need to be cascaded as the task
                    # has already been canceled.
                    pass
                else:
                    try:
                        # got a valid result so put it back.
                        self.task_done()
                        self.put_nowait(r)
                    except Exception as e:
                        # at this point, the task is canceled so
                        # we can't raise another exception, but we
                        # should log that an error has occurred.
                        # It's an unlikely situation, but definitely a
                        # bug in the code.
                        pkdlog(
                            'exception={} unable to put back result={} stack={}',
                            e,
                            r,
                            pkdexc(),
                        )
            raise
