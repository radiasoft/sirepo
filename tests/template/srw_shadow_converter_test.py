# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw_shadow_converter`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest

def test_convert_srw_to_shadow():
    from pykern import pkio, pkjson
    from pykern.pkunit import pkeq
    from sirepo.template.srw_shadow_converter import SRWShadowConverter

    with pkunit.save_chdir_work():
        for name in ('crl', 'gaussian', 'grating'):
            srw = _read_json_from_data_dir(f'{name}-srw.json')
            actual = SRWShadowConverter().srw_to_shadow(srw.models)
            del actual['version']
            pkjson.dump_pretty(actual, f'{name}-shadow.json')
            expect = _read_json_from_data_dir(f'{name}-shadow.json')
            pkeq(expect, actual)


def _read_json_from_data_dir(name):
    from pykern import pkio, pkjson
    return pkjson.load_any(pkio.read_text(pkunit.data_dir().join(name)))
