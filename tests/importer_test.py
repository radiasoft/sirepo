# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')

def test_import_zip():
    from pykern import pkio
    from pykern import pkunit
    from pykern import pkcollections
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern.pkunit import pkeq, pkfail, pkok
    from sirepo import sr_unit
    import re
    import string
    import StringIO

    fc = sr_unit.flask_client()
    for f in pkio.sorted_glob(pkunit.data_dir().join('*.zip')):
        sim_type = re.search(r'^([a-z]+)_', f.basename).group(1)
        try:
            res = fc.sr_post_form(
                'importFile',
                {
                    'file': (open(str(f), 'rb'), f.basename),
                    'folder': '/',
                },
                {'simulation_type': sim_type},
            )
        except Exception as e:
            if not 'deviance' in f.basename:
                raise
            expect = re.search(r'Error: (.+)', json).group(1)
            pkeq(expect, str(e))
            continue
        pkok(not 'error' in res, res.get('error'))
