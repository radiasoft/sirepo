# -*- coding: utf-8 -*-
u"""time functions (artificial time)

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
import datetime
import sirepo.request
import sirepo.util
import time


#: POSIX epoch as object
EPOCH = datetime.datetime.utcfromtimestamp(0)

#: Adjustment of system time
_timedelta = None

#: Whether or not this module has been initilaized
_initialized = False

def adjust_time(days):
    """Shift the system time by days

    Args:
        days (str): must be integer. If None or 0, no adjustment.
    """
    def _adjust_supervisor_srtime():
        import sirepo.job_api

        if sirepo.util.flask_app():
            sirepo.job_api.adjust_supervisor_srtime(d)

    global _timedelta
    _timedelta = None
    try:
        d = int(days)
        if d != 0:
            _timedelta = datetime.timedelta(days=d)
        _adjust_supervisor_srtime()
    except Exception:
        _timedelta = None
        pass


class Request(sirepo.request.Base):
    @api_perm.allow_visitor
    def api_adjustTime(self, days=None):
        """Shift the system time by days and get the adjusted time
    
        Args:
            days (str): must be integer. If None or 0, no adjustment.
        """
        from sirepo import http_reply
    
        assert pkconfig.channel_in_internal_test(), \
            'API forbidden'
        adjust_time(days)
        return http_reply.gen_json_ok({
            'adjustedNow': utc_now().isoformat(),
            'systemNow': datetime.datetime.utcnow().isoformat(),
        })


def init():
    global _initialized, utc_now_as_int
    if _initialized:
        return
    _initialized = True
    if not pkconfig.channel_in_internal_test():
        global utc_now_as_float, utc_now
        utc_now_as_float = time.time
        utc_now = datetime.datetime.utcnow
    utc_now_as_int = lambda: int(utc_now_as_float())


def init_apis(*args, **kwargs):
    init()


def to_timestamp(dt):
    """Convert datetime into float seconds from epoch

    Args:
        dt (datetime): datetime object

    Returns:
        float: seconds since epoch
    """
    return (dt - EPOCH).total_seconds()


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
    return to_timestamp(utc_now())


def utc_now_as_milliseconds():
    """Adjusted POSIX time as milliseconds

    Returns:
        int: adjusted `time.time` as milliseconds
    """
    return int(utc_now_as_float() * 1000)
