"""test user alert

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def setup_module(module):
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_HOME_PAGE_SUBDIR="wp_en2",
    )


def test_home_page(fc):
    from pykern import pkunit
    import re

    r = fc.sr_get("/", redirect=True)
    r.assert_http_status(200)
    pkunit.pkre("Sirepo by RadiaSoft", r.data)
    for u in set(re.findall(r'(?:href|src)="(/en/[^"?]+)', r.data)):
        fc.sr_get(u).assert_http_status(200)
