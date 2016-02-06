# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.sirepo_parser`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkio
from pykern import pkunit

from sirepo.sirepo_parser import main


def test_sirepo_parser():
    with pkunit.save_chdir_work():
        for b in ('t1', ): # 't2', 't3',):
            in_py = str(pkunit.data_dir().join('{}.py'.format(b)))
            main(in_py, debug=False)
            actual_fn = 'parsed_sirepo.json'
            actual = pkio.read_text(actual_fn)
            expect_fn = pkunit.data_dir().join('{}.json'.format(b))
            expect = pkio.read_text(expect_fn)
            assert expect == actual, \
                '{} should match expected {}'.format(actual_fn, expect_fn)
