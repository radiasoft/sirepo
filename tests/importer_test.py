# -*- coding: utf-8 -*-
u"""sipepo.importer test

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_import_json(fc):
    from sirepo import srunit

    _do(fc, 'json', lambda f: f.read(mode='rb'))


def test_import_python(fc):
    from sirepo import srunit

    _do(fc, 'py', lambda f: f.read(mode='rb'))


def test_import_zip(fc):
    import zipfile

    def _parse(fn):
        z = zipfile.ZipFile(str(fn))
        json = ''
        try:
            with z.open('sirepo-data.json') as f:
                json = f.read()
        except Exception:
            pass
        return json

    _do(fc, 'zip', _parse)


def _do(fc, file_ext, parse):
    from pykern.pkcollections import PKDict
    from pykern import pkio
    from pykern import pkunit
    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkfail, pkok, pkre
    import re

    for suffix in '', ' 2', ' 3':
        for f in pkio.sorted_glob(pkunit.data_dir().join('*.' + file_ext)):
            json = parse(f)
            sim_type = re.search(r'^([a-z]+)_', f.basename).group(1)
            fc.sr_get_root(sim_type)
            is_dev = 'deviance' in f.basename
            res = fc.sr_post_form(
                'importFile',
                PKDict(folder='/importer_test'),
                PKDict(simulation_type=sim_type),
                file=f,
            )
            if file_ext == 'py':
                sim_name = f.purebasename
            elif is_dev:
                m = re.search(r'Error: (.+)', json)
                if m:
                    expect = m.group(1)
                    pkre(expect, res.error)
                continue
            else:
                sim_name = pkcollections.json_load_any(json).models.simulation.name
            pkeq(sim_name + suffix, res.models.simulation.name)
