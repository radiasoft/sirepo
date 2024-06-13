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


def test_render_resource():
    from sirepo import resource
    from pykern.pkcollections import PKDict
    from pykern import pkunit
    from pykern import pkio

    pkunit.pkre(
        'var = "x"',
        pkio.read_text(
            resource.render_jinja(
                "resource_test_data",
                "README.txt",
                target_dir=pkunit.work_dir(),
                j2_ctx=PKDict(
                    var="x",
                ),
            )
        ),
    )
