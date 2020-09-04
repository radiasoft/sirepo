# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest


def test_importer(import_req):
    from pykern.pkcollections import PKDict
    from sirepo.template import lattice
    from sirepo.template import elegant
    import sirepo.lib
    import sirepo.util
    import flask

    for fn in pkio.sorted_glob(pkunit.data_dir().join('*')):
        if not pkio.has_file_extension(fn, ('ele', 'lte')) \
            or fn.basename.endswith('.ele.lte'):
            continue
        k = PKDict()
        pkdlog('file={}', fn)
        if fn.basename.startswith('deviance-'):
            try:
                data = elegant.import_file(import_req(fn))
            except Exception as e:
                k.actual = f'{e}\n'
            else:
                k.actual = 'did not raise exception'
        elif fn.ext == '.lte':
            data = elegant.import_file(import_req(fn))
            data['models']['commands'] = []
            j = elegant._Generate(data, is_parallel=True).jinja_env
            k.actual = j.rpn_variables + j.lattice
        else:
            f = sirepo.lib.Importer('elegant').parse_file(fn).write_files(pkunit.work_dir())
            k.actual_path = f.commands
        pkunit.file_eq(fn.basename + '.txt', **k)
