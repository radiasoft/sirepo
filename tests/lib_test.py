# -*- coding: utf-8 -*-
u"""Test lib.Importer

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import pytest

def test_elegant():
    _code()


def test_opal():
    _code()


def _code():
    from pykern import pkunit, pkio, pkjson
    from pykern.pkdebug import pkdp
    import inspect
    import sirepo.lib
    for i, s in enumerate(pkio.sorted_glob(pkunit.data_dir().join(
            f'{inspect.stack()[1].function.split("_")[1]}_*',
    ))):
        t = s.basename.split('_')[0]
        d = sirepo.lib.Importer(t, ignore_files=['Should_be_ignored.T7']).parse_file(
            pkio.sorted_glob(s.join('first*'))[0]
        )
        pkdp('\n\n\n ** D: {}', d)
        d2 = d.copy()
        d2.pkdel('version')
        d2.models.simulation.pkdel('lastModified')
        for k in [k for k in d2.keys() if '_SimData__' in k]:
            d2.pkdel(k)
        pkunit.file_eq(s.join('out.json'), d2)
        w = pkunit.work_dir().join(s.basename)
        r = d.write_files(w)
        assert not w.join('Should_be_ignored.T7').check(link=True)
        pkjson.dump_pretty(r.output_files, filename=w.join('output_files.json'))
        for o in pkio.sorted_glob(pkunit.data_dir().join(s.basename, '*.out')):
            pkunit.file_eq(o, actual_path=w.join(o.basename).new(ext=''))

