# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_srw_create_predefined():
    from pykern import pkunit
    from pykern import pkjson
    import sirepo.pkcli.srw

    d = pkunit.empty_work_dir()
    sirepo.pkcli.srw.create_predefined(d)
    j = pkjson.load_any(d.listdir()[0])
    pkunit.pkeq(22, len(j.beams))
