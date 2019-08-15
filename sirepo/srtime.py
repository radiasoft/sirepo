# -*- coding: utf-8 -*-
u"""time functions (artificial time)

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
import datetime
import time


#: Adjustment of system time
_timedelta = None

#: POSIX epoch as object
_epoch = datetime.datetime.utcfromtimestamp(0)


@api_perm.allow_visitor
def api_adjustTime(days=None):
    """Shift the system time by days

    Args:
        days (str): must be integer. if None, no adjustment.
    """
    from sirepo import http_reply

    global _timedelta
    _timedelta = None
    try:
        d = int(days)
        if d != 0:
            _timedelta = datetime.timedelta(days=d)
    except Exception:
        pass
    return http_reply.gen_json_ok({
        'adjustedNow': utc_now().isoformat(),
        'systemNow': datetime.datetime.utcnow().isoformat(),
    })


def init_apis(*args, **kwargs):
    pass


def utc_now():
    """Adjusted UTC time as object

    Returns:
        datetime.datetime: adjusted `datetime.datetime.utcnow`
    """
    assert pkconfig.channel_in_internal_test()
    if _timedelta is None:
        return datetime.datetime.utcnow()
    return datetime.datetime.utcnow() + _timedelta


def utc_now_as_float():
    """Adjusted POSIX time as a float

    Returns:
        float: adjusted `time.time`
    """
    assert pkconfig.channel_in_internal_test()
    if _timedelta is None:
        return time.time()
    res = utc_now() - _epoch;
    return res.total_seconds()


def _init():
    if pkconfig.channel_in_internal_test():
        from sirepo import uri_router
        uri_router.register_api_module()
    else:
        global utc_now_as_float, utc_now
        utc_now_as_float = time.time
        utc_now = datetime.datetime.utcnow


_init()
