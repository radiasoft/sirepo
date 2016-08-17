# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp
import pytest

pytest.importorskip('sdds')

#TODO(pjm): use glob to find data files
_FILES = ['aps.lte', 'fodo.lte', 'fourDipoleCSR.lte', 'full457MeV.lte', 'LCLS21Feb08.lte', 'multiple.lte', 'invalid.lte', 'bad-rpn.lte', 'BYBL.lte', 'slc.lte', 'par.lte', 'lattice.lte', 'apsKick.lte', 'lattice-with-rpns.lte']

class TestFlaskRequest(object):
    def __init__(self, filename):
        self.filename = filename
        self.files = {
            'file': self,
        }
    def read(self):
        with open(str(pkunit.data_dir().join(self.filename))) as f:
            return f.read()


def test_importer():
    from sirepo.template import elegant
    with pkunit.save_chdir_work():
        for filename in _FILES:
            error, data = elegant.import_file(TestFlaskRequest(filename))
            outfile = '{}.txt'.format(filename)
            if error:
                actual = error
            else:
                actual = elegant.generate_lattice(data, {})
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            assert expect == actual
