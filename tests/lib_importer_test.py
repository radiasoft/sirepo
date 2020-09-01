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
        w = pkunit.work_dir().join(s.basename)
        shutil.copytree(s, w)
        with pkio.save_chdir(w):
            d = sirepo.lib.Importer(w.basename.split('_')[0]).parse_file(
                pkio.sorted_glob(w.join('first*'))[0].basename,
            )
            d.pkdel('version')
            o = 'out.json'
            pkunit.file_eq(s.join(o), d, w.join(o))
