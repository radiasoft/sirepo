# -*- coding: utf-8 -*-
u"""sipepo.importer test

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')


def test_import_json():
    from sirepo import srunit
    _do('json', srunit.file_as_stream)


def test_import_zip():
    import zipfile

    def _parse(fn):
        z = zipfile.ZipFile(str(fn))
        json = ''
        try:
            with z.open('sirepo-data.json') as f:
                json = f.read()
        except Exception:
            pass
        return json, open(str(fn), 'rb')

    _do('zip', _parse)


def _do(file_ext, parse):
    from pykern import pkio
    from pykern import pkunit
    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkfail, pkok
    from sirepo import srunit
    import re

    fc = srunit.flask_client(sim_types='srw:myapp')
    fc.sr_login_as_guest()
    for suffix in '', ' 2', ' 3':
        for f in pkio.sorted_glob(pkunit.data_dir().join('*.' + file_ext)):
            json, stream = parse(f)
            sim_type = re.search(r'^([a-z]+)_', f.basename).group(1)
            fc.sr_get_root(sim_type)
            is_dev = 'deviance' in f.basename
            if not is_dev:
                sim_name = pkcollections.json_load_any(json).models.simulation.name
            res = fc.sr_post_form(
                'importFile',
                {
                    'file': (stream, f.basename),
                    'folder': '/importer_test',
                },
                {'simulation_type': sim_type},
            )
            if is_dev:
                m = re.search(r'Error: (.+)', json)
                if m:
                    expect = m.group(1)
                    pkeq(expect, res.error)
                continue
            pkeq(sim_name + suffix, res.models.simulation.name)
