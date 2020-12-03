# -*- coding: utf-8 -*-
u"""Test lib.Importer

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import pytest

def test_elegant():
    _code([['%s.cen']])


def test_opal():
    _code()


def _code(files=None):
    from pykern import pkunit, pkio, pkjson
    from pykern.pkdebug import pkdp
    import inspect
    import sirepo.lib

    for i, s in enumerate(pkio.sorted_glob(pkunit.data_dir().join(
            f'{inspect.stack()[1].function.split("_")[1]}_*',
    ))):
        t = s.basename.split('_')[0]
        d = sirepo.lib.Importer(t).parse_file(
            pkio.sorted_glob(s.join('first*'))[0]
        )
        d2 = d.copy()
        d2.pkdel('version')
        for k in [k for k in d2.keys() if '_SimData__' in k]:
            d2.pkdel(k)
        pkunit.file_eq(s.join('out.json'), d2)
        w = pkunit.work_dir().join(s.basename)
        r = d.write_files(w)
        for o in pkio.sorted_glob(pkunit.data_dir().join(s.basename, '*.out')):
            pkunit.file_eq(o, actual_path=w.join(o.basename).new(ext=''))
        if files:
            pkunit.pkok(
                set(files[i]).issubset(set(r.output_files)),
                'expecting files={} to be subset of output_files={}',
                files,
                r.output_files,
            )
