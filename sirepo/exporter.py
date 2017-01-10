# -*- coding: utf-8 -*-
u"""Export simulations in a single archive


:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
from pykern import pkio
from sirepo import simulation_db
from sirepo.template import template_common
import os.path
import py.path
import zipfile


def create_zip(sim_type, sim_id):
    """Zip up the json file and its dependencies

    Args:
        sim_type (str): simulation type
        sim_id (str): simulation id

    Returns:
        py.path.Local: zip file name
    """
    #TODO(robnagler) need a lock
    with pkio.save_chdir(simulation_db.tmp_dir()):
        res = py.path.local(sim_id + '.zip')
        data = simulation_db.open_json_file(sim_type, sid=sim_id)
        with zipfile.ZipFile(
            str(res),
            mode='w',
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
        ) as z:
            for f in [simulation_db.sim_data_file(sim_type, sim_id)] \
                + template_common.lib_files(data):
                z.write(str(f), f.basename)
    return res
