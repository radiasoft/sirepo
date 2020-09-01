# -*- coding: utf-8 -*-
u"""Public functions from sirepo

Use this to call sirepo from other packages or Python notebooks.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio


class SimData(PKDict):

    def __init__(self, data):
        self.update(data)
        self.pkdel('report')
        self.models.pkdel('simulation')


class Importer:

    def __init__(self, sim_type):
        import sirepo.template

        self._template = sirepo.template.import_module(sim_type)

    def parse_file(self, path):
        assert hasattr(self._template, 'parse_input_text'), \
            f'{self._template.SIM_TYPE} does not support parsing'
        p = pykern.pkio.py_path(path)
        with pykern.pkio.save_chdir(p.dirname):
            return SimData(
                self._template.lib_importer_parse_file(p),
            )
