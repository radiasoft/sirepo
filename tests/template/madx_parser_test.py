# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.madx_parser`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest


def test_extract_tfs_pages():
    from pykern.pkunit import pkeq
    from sirepo.template import madx_parser

    path = pkunit.data_dir().join('ptc_track.file.tfs')
    header = madx_parser.parse_tfs_file(path, header_only=True)
    pkeq(
        header,
        ['number', 'turn', 'x', 'px', 'y', 'py', 't', 'pt', 's', 'e']
    )
    info = madx_parser.parse_tfs_page_info(path)
    pkeq(
        info[3],
        dict(
            name='BPMY1',
            turn='1',
            s='2.72',
        ),
    )
    res = madx_parser.parse_tfs_file(path, want_page=3)
    pkeq(len(res.s), 5)
    pkeq(res.s[0], info[3].s)
    res = madx_parser.parse_tfs_file(path)
    pkeq(len(res.s), 75)


def test_parse_madx_file():
    from pykern import pkio, pkjson
    from pykern.pkunit import pkeq
    from sirepo.template import madx, madx_parser

    for name in ('particle_track', ):
        actual = madx_parser.parse_file(pkio.read_text(
            pkunit.data_dir().join(f'{name}.madx')))
        madx._fixup_madx(actual)
        del actual['version']
        expect = pkjson.load_any(pkunit.data_dir().join(f'{name}.json'))
        pkeq(expect, actual)


def test_parse_madx_file_downcase():
    from sirepo.template import madx_parser
    import re
    parsed = madx_parser.parse_file('''
        REAL energy = 1.6;
        REAL gamma = (ENERGY + 0.0005109989) / 0.0005109989;
    ''', True)
    assert re.search(r'energy', str(parsed))
    assert not re.search(r'ENERGY', str(parsed))

def test_parse_tfs_file():
    from pykern.pkunit import pkeq
    from sirepo.template import madx_parser

    path = pkunit.data_dir().join('twiss.file.tfs')
    res = madx_parser.parse_tfs_file(path)
    pkeq(
        res.betx,
        ['11.639', '14.73204923'],
    )
    pkeq(
        res.name,
        ['"RING$START"', '"D3"'],
    )
    pkeq(
        res.sig44,
        ['1.048547761e-07', '1.048547761e-07'],
    )
    pkeq(
        res.n1,
        ['0', '0'],
    )
