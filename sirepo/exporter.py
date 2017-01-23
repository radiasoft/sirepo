# -*- coding: utf-8 -*-
u"""Export simulations in a single archive

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import os.path
import py.path
import zipfile


def create_archive(sim_type, sim_id, filename):
    """Zip up the json file and its dependencies

    Args:
        sim_type (str): simulation type
        sim_id (str): simulation id
        filename (str): for file type

    Returns:
        py.path.Local: zip file name
    """
    from pykern import pkio
    from sirepo import uri_router

    if not pkio.has_file_extension(filename, ('zip', 'html')):
        raise uri_router.NotFound(
            '{}: unknown file type; expecting html or zip',
            filename,
        )
    fp, data = _create_zip(sim_type, sim_id)
    if filename.endswith('zip'):
        return fp, 'application/zip'
    return _create_html(fp, data)


def _create_html(zip_path, data):
    """Convert zip to html data

    Args:
        zip_path (py.path): what to embed
        data (dict): simulation db
    Returns:
        py.path, str: file and mime type
    """
    from pykern import pkjinja
    from pykern import pkcollections
    from sirepo import uri_router
    import py.path
    import copy

    # Use same tmp directory
    fp = py.path.local(zip_path.dirname).join(zip_path.purebasename) + '.html'
    values = pkcollections.Dict(data=data)
    values.uri = uri_router.uri_for_api('importArchive')
    values.company = 'RadiaSoft'
    values.zip = zip_path.read().encode('base64')
    with open(str(fp), 'wb') as f:
        fp.write(pkjinja.render_resource('archive.html', values))
    return fp, 'text/html'


def _create_zip(sim_type, sim_id):
    """Zip up the json file and its dependencies

    Args:
        sim_type (str): simulation type
        sim_id (str): simulation id

    Returns:
        py.path.Local: zip file name
    """
    from pykern import pkio
    from sirepo import simulation_db
    from sirepo.template import template_common

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
    return res, data
