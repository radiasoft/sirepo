# -*- coding: utf-8 -*-
"""test sirepo.resource

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp


def test_static_files():
    from sirepo import resource
    from pykern import pkdebug, pkunit

    x = list(resource.static_files())
    pkunit.pkok(
        list(filter(lambda y: y[0] == "static/json/myapp-schema.json", x)),
        "myapp-schema not in list={}",
        x,
    )


def test_render_resource():
    from sirepo import resource
    from pykern import pkunit

    d = pkunit.data_dir()
    pkunit.file_eq(
        d.join("expect.py"),
        actual_path=resource.render_resource(
            "actual.py",
            d,
            pkunit.work_dir(),
            PKDict(
                x="x",
                y="y",
            ),
        ),
    )
