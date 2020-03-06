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
from sirepo import srunit


def test_importer(import_req):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template import lattice
    from sirepo.template import elegant
    import sirepo.util
    import flask

    with pkunit.save_chdir_work():
        for fn in pkio.sorted_glob(pkunit.data_dir().join('*')):
            if not pkio.has_file_extension(fn, ('ele', 'lte')) \
                or fn.basename.endswith('ele.lte'):
                continue
            error = None
            try:
                data = elegant.import_file(import_req(fn))
            except Exception as e:
                pkdlog(pkdexc())
                error = str(e)
            if error:
                actual = error
            else:
                if pkio.has_file_extension(fn, 'lte'):
                    data['models']['commands'] = []
                    actual = '{}{}'.format(
                        elegant._generate_variables(data),
                        elegant._generate_lattice(
                            elegant._build_filename_map(data),
                            lattice.LatticeUtil(data, elegant._SCHEMA),
                        ),
                    )
                else:
#TODO(robnagler) test simulationId
                    data2 = elegant.import_file(import_req(fn.new(ext='ele.lte')), test_data=data)
                    actual = elegant._generate_commands(
                        elegant._build_filename_map(data2),
                        lattice.LatticeUtil(data2, elegant._SCHEMA),
                    )
            outfile = fn.basename + '.txt'
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            pkeq(expect, actual)
