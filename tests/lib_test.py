# -*- coding: utf-8 -*-
u"""Test lib.Importer

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_elegant():
    from pykern.pkdebug import pkdp
    from pykern import pkunit, pkio, pkjson
    import sirepo.lib
    import shutil

    for s in pkio.sorted_glob(pkunit.data_dir().join('*')):
        t = s.basename.split('_')[0]
        with pkio.save_chdir(s):
            d = sirepo.lib.Importer(t).parse_file(
                pkio.sorted_glob('first*')[0].basename,
            )
        d2 = d.copy()
        d2.pkdel('version')
        for k in [k for k in d2.keys() if '_SimData__' in k]:
            d2.pkdel(k)
        pkunit.file_eq(s.join('out.json'), d2)
        d.write_files(pkunit.work_dir().join(s.basename))
