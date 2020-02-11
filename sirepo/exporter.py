# -*- coding: utf-8 -*-
u"""Export simulations in a single archive

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdp
from sirepo import sim_data
from sirepo import simulation_db
from sirepo import uri_router
import sirepo.http_reply
import copy
import sirepo.util
import zipfile


def create_archive(sim):
    """Zip up the json file and its dependencies

    Args:
        sim (PKDict): parsed request

    Returns:
        py.path.Local: zip file name
    """
    if not pkio.has_file_extension(sim.filename, ('zip', 'html')):
        raise sirepo.util.NotFound(
            'unknown file type={}; expecting html or zip'.format(sim.filename),
        )
    with simulation_db.tmp_dir() as d:
        want_zip = sim.filename.endswith('zip')
        f, c = create_zip(sim, want_python=want_zip, path=d.join(sim.id + '.zip'))
        if want_zip:
            t = 'application/zip'
        else:
            f, t = _create_html(f, c)
        return sirepo.http_reply.gen_file_as_attachment(
            f,
            content_type=t,
            filename=sim.filename,
        )


def create_zip(sim, want_python, path=None):
    """Zip up the json file and its dependencies

    Args:
        sim (req): simulation
        want_python (bool): include template's python source?
        path (py.path): absoulte path of zip file to write files to

    Returns:
        py.path.Local: zip file name
    """
    data = simulation_db.open_json_file(sim.type, sid=sim.id)
    data.pkdel('report')
    simulation_db.update_rsmanifest(data)
    files = sim_data.get_class(data).lib_files_for_export(data)
    files.insert(0, simulation_db.sim_data_file(sim.type, sim.id))
    if want_python:
        files.append(_python(data))
    with zipfile.ZipFile(
        str(path),
        mode='w',
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as z:
        for f in files:
            z.write(str(f), f.basename)
    return path, data


def _create_html(zip_path, data):
    """Convert zip to html data

    Args:
        zip_path (py.path): what to embed
        data (dict): simulation db
    Returns:
        py.path, str: file and mime type
    """
    # Use same tmp directory
    fp = zip_path.new(ext='.html')
    values = pkcollections.Dict(data=data)
    values.uri = uri_router.uri_for_api('importArchive', external=False)
    values.server = uri_router.uri_for_api('importArchive')[:-len(values.uri)]
    sc = simulation_db.SCHEMA_COMMON
    values.appLongName = sc.appInfo[data.simulationType].longName
    values.appShortName = sc.appInfo[data.simulationType].shortName
    values.productLongName = sc.productInfo.longName
    values.productShortName = sc.productInfo.shortName
    values.zip = zip_path.read().encode('base64')
    with open(str(fp), 'wb'):
        fp.write(pkjinja.render_resource('archive.html', values))
    return fp, 'text/html'


def _python(data):
    """Generate python in current directory

    Args:
        data (dict): simulation

    Returns:
        py.path.Local: file to append
    """
    import sirepo.template
    import copy

    template = sirepo.template.import_module(data)
    res = pkio.py_path('run.py')
    res.write(template.python_source_for_model(copy.deepcopy(data), None))
    return res
