# -*- coding: utf-8 -*-
"""PyTest for `sirepo.template.template_common.LogParser`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest



def test_activait_logparser():
    from sirepo.template import activait


    d = pkunit.data_dir()
    res = activait._parse_activate_log(d, log_filename="activait1.txt")
    print("res", res)


def test_srw_logparser():
    from sirepo.template import template_common


    d = pkunit.data_dir()
    for i in range(2):
        res = template_common.LogParser(
            d,
            log_filename=f"srw{i + 1}.txt"
        ).parse_for_errors()
        print(f"res {i + 1}: ", res)


def test_cloudmc_logparser():
    from sirepo.template import cloudmc


    d = pkunit.data_dir()
    # TODO (gurhar1133): also just doesn't seem to be working
    res = cloudmc._parse_cloudmc_log(d, log_filename="cloudmc1.txt")
    print("res: ", res)


def test_opal_logparser():
    from sirepo.template import opal


    d = pkunit.data_dir()
    for i in range(4):
        res = opal._OpalLogParser(
            d,
            log_filename=f"opal{i + 1}.txt"
        ).parse_for_errors()
        print(f"res:{i + 1} ", res)


def test_shadow_logparser():
    from sirepo.template import shadow


    d = pkunit.data_dir()
    res = shadow._parse_shadow_log(d, log_filename="shadow1.txt")
    print("res:", res)