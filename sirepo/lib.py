# -*- coding: utf-8 -*-
u"""Public functions from sirepo

Use this to call sirepo from other packages or Python notebooks.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import copy
import pykern.pkio


class Importer:

    def __init__(self, sim_type):
        import sirepo.template

        self.__adapter = sirepo.template.import_module(sim_type).LibAdapter()

    def parse_file(self, path):
        p = pykern.pkio.py_path(path)
        with pykern.pkio.save_chdir(p.dirpath()):
            return SimData(
                self.__adapter.parse_file(p),
                p,
                self.__adapter,
            )


class SimData(PKDict):
    """Represents data of simulation"""

    def __init__(self, data, source, adapter):
        super().__init__(data)
        self.pkdel('report')
        self.__source = source
        self.__adapter = adapter

    def copy(self):
        """Allows copy.deepcopy"""
        return self.__class__(self, self.__source, self.__adapter)

    def write_files(self, dest_dir):
        """Writes files for simulation state

        Args:
            dest_dir (str or py.path): where to write files
        Returns:
            PKDict: files written (debugging only)
        """
        return self.__adapter.write_files(
            # need to make a copy, b/c generate_parameters_file modifies
            copy.deepcopy(self),
            self.__source,
            pykern.pkio.py_path(dest_dir),
        )
