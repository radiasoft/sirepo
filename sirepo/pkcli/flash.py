# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common


def run(cfg_dir):
    # this is called for initZipReport only
    cfg_dir = pkio.py_path(cfg_dir)
    r = template_common.exec_parameters()
    r.results.filesHash = _sim_data().flash_problem_files_archive_hash(
        cfg_dir.join(_sim_data().flash_app_archive_basename()),
    )
    template_common.write_sequential_result(r.results)


def _sim_data():
    import sirepo.sim_data
    return sirepo.sim_data.get_class('flash')
