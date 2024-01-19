# -*- coding: utf-8 -*-
"""SRW call tracer

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog
import array
import pykern.pkjson
import srwlpy
import srwpy.srwlpy

_MAX_ARRAY_VALUES = 40

CalcElecFieldSR = srwpy.srwlpy.CalcElecFieldSR
PropagElecField = srwpy.srwlpy.PropagElecField
CalcPartTraj = srwpy.srwlpy.CalcPartTraj
call_count = 0


def patchedCalcElecFieldSR(*args):
    _dump("CalcElecFieldSR", ["wfr", "partTraj", "magFldCnt", "precPar"], args)
    return CalcElecFieldSR(*args)


def patchedPropagElecField(*args):
    _dump("PropagElecField", ["wfr", "optCnt", "radView"], args)
    return PropagElecField(*args)


def patchedCalcPartTraj(*args):
    _dump("CalcPartTraj", ["partTraj", "magFldCnt", "prec"], args)
    return CalcPartTraj(*args)


def instrument_methods():
    srwpy.srwlpy.CalcElecFieldSR = patchedCalcElecFieldSR
    srwlpy.CalcElecFieldSR = patchedCalcElecFieldSR
    srwpy.srwlpy.PropagElecField = patchedPropagElecField
    srwlpy.PropagElecField = patchedPropagElecField
    srwpy.srwlpy.CalcPartTraj = patchedCalcPartTraj
    srwlpy.CalcPartTraj = patchedCalcPartTraj


def _dump(method, names, args):
    global call_count
    call_count += 1
    r = PKDict(method=method, call_count=call_count, args=PKDict())
    for i, n in enumerate(names):
        if len(args) > i:
            r.args[n] = _dump_value(args[i])
    pkdlog("\n{}", pykern.pkjson.dump_pretty(r))


def _dump_value(value):
    if (
        isinstance(value, int)
        or isinstance(value, float)
        or isinstance(value, str)
        or value is None
    ):
        return value
    if isinstance(value, bytes):
        return f"<{ len(value) } bytes>"
    if isinstance(value, array.array):
        if len(value) > _MAX_ARRAY_VALUES:
            return f"<{ len(value) } array.array values>"
        return [_dump_value(x) for x in value]
    if isinstance(value, dict):
        return {k: _dump_value(value[k]) for k in value}
    if isinstance(value, list):
        return [_dump_value(x) for x in value]
    if isinstance(value, object):
        return [type(value).__name__, _dump_value(value.__dict__)]
    raise AssertionError("unhandled type: {}".format(type(value)))


instrument_methods()
