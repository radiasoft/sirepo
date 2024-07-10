# -*- coding: utf-8 -*-
"""Wrappers for Tornado

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdlog, pkdexc
import sirepo.const
import sirepo.http_util
import tornado.locks
import tornado.queues


class Event(tornado.locks.Event):
    """Event with ordered waiters.

    When the event is set the waiters are awoken in a FIFO order.
    """

    class _OrderedWaiters(list):
        def add(self, val):
            self.append(val)

    def __init__(self):
        super().__init__()
        self._waiters = self._OrderedWaiters()


class AuthHeaderRequestHandler(tornado.web.RequestHandler):
    @classmethod
    def get_header(cls, token):
        return sirepo.http_util.auth_header(token)

    async def get(self, *args, **kwargs):
        await self._sr_get(self.__authenticate())

    async def post(self, *args, **kwargs):
        await self._sr_post(self.__authenticate())

    async def put(self, *args, **kwargs):
        await self._sr_put(self.__authenticate())

    def __authenticate(self):
        if m := sirepo.http_util.parse_auth_header(self.request.headers):
            return self._sr_authenticate(m)
        raise error_forbidden()


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
        except sirepo.const.ASYNC_CANCELED_ERROR:
            if x:
                try:
                    r = x.result()
                except BaseException:
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
                    except BaseException as e:
                        # at this point, the task is canceled so
                        # we can't raise another exception, but we
                        # should log that an error has occurred.
                        # It's an unlikely situation, but definitely a
                        # bug in the code.
                        pkdlog(
                            "exception={} unable to put back result={} stack={}",
                            e,
                            r,
                            pkdexc(),
                        )
            raise


def error_forbidden():
    return tornado.web.HTTPError(403)


def error_not_found():
    return tornado.web.HTTPError(404)
