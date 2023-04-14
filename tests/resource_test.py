# -*- coding: utf-8 -*-
"""test sirepo.resource

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_static_files():
    from sirepo import resource
    from pykern import pkdebug, pkunit

    x = list(resource.static_files())
    pkunit.pkok(
        list(filter(lambda y: y[0] == "static/json/myapp-schema.json", x)),
        "myapp-schema not in list={}",
        x,
    )
