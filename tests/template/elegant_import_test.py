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

pytest.importorskip('sdds')


class FlaskRequest(object):

    def __init__(self, filename):
        self.filename = str(filename)
        self.files = {
            'file': self,
        }
        self.form = {}

    def read(self):
        return pkio.read_text(self.filename)


def test_importer():
    from pykern import pkcollections
    from pykern import pkio
    from pykern.pkunit import pkeq
    from sirepo.template import beamline
    from sirepo.template import elegant

    with pkunit.save_chdir_work():
        for fn in pkio.sorted_glob(pkunit.data_dir().join('*')):
            if not pkio.has_file_extension(fn, ('ele', 'lte')) \
                or fn.basename.endswith('ele.lte'):
                continue
            error = None
            try:
                data = elegant.import_file(FlaskRequest(fn))
            except Exception as e:
                pkdlog(pkdexc())
                error = e.message
            if error:
                actual = error
            else:
                if pkio.has_file_extension(fn, 'lte'):
                    data['models']['commands'] = []
                    actual = '{}{}'.format(
                        elegant._generate_variables(data),
                        elegant.generate_lattice(
                            data,
                            elegant._build_filename_map(data),
                            beamline.build_beamline_name_map(data),
                            pkcollections.Dict(),
                        ),
                    )
                else:
                    data2 = elegant.import_file(FlaskRequest('{}.lte'.format(fn)), test_data=data)
                    actual = elegant._generate_commands(
                        data2,
                        elegant._build_filename_map(data2),
                        beamline.build_beamline_name_map(data2),
                        pkcollections.Dict(),
                    )
            outfile = fn.basename + '.txt'
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            #TODO(pjm): this takes too long if there are a lot of diffs
            #assert expect == actual
            pkeq(expect, actual)
