# -*- coding: utf-8 -*-
u"""Test for uniquifying a madx beamline

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_uniquify_beamline():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkunit import pkeq
    from pykern import pkjson
    from sirepo.template import madx

    d = pkjson.load_any(pkunit.data_dir().join('in.json'))
    madx.uniquify_elements(d)
    pkeq(1, len(d.models.beamlines), 'expecting one beamline={}', d.models.beamlines)
    l = d.models.beamlines[0]['items']
    pkeq(len(list(set(l))), len(l), 'expecting all unique items={}', l)
    e = {e._id: e.original_id for e in d.models.elements}
    r = [e[i] for i in d.models.beamlines[0]['items']]
    pkeq(
        [2, 2, 5, 5, 5, 2, 2, 5, 5, 5, 2, ],
        r,
        'expecting proper reflection of sub-lines. ids of original elements: {}',
        r
    )
