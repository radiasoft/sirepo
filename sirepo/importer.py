# -*- coding: utf-8 -*-
u"""Import a single archive

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from pykern import pkcompat
import base64
import pykern.pkio
import sirepo.http_request
import sirepo.util
import six
import zipfile


def do_form(form):
    """Self-extracting archive post

    Args:
        form (flask.request.Form): what to import

    Returns:
        dict: data
    """
    from sirepo import simulation_db

    if not 'zip' in form:
        raise sirepo.util.raise_not_found('missing zip in form')
    data = read_zip(base64.decodebytes(pkcompat.to_bytes(form['zip'])))
    data.models.simulation.folder = '/Import'
    data.models.simulation.isExample = False
    return simulation_db.save_new_simulation(data)


def read_json(text, sim_type=None):
    """Read json file and return

    Args:
        text (IO): file to be read
        sim_type (str): expected type

    Returns:
        dict: data
    """
    from sirepo import simulation_db

    # attempt to decode the input as json first, if invalid try python
    # fixup data in case new structures are need for lib_file ops below
    data = simulation_db.fixup_old_data(simulation_db.json_load(text))[0]
    assert not sim_type or data.simulationType == sim_type, \
        'simulationType={} invalid, expecting={}'.format(
            data.simulationType,
            sim_type,
        )
    return sirepo.http_request.parse_post(req_data=data).req_data


def read_zip(zip_bytes, sim_type=None):
    """Read zip file and store contents

    Args:
        zip_bytes (bytes): bytes to read
        sim_type (module): expected app

    Returns:
        dict: data
    """
    from sirepo import simulation_db
    import sirepo.sim_data

    with simulation_db.tmp_dir() as tmp:
        data = None
        zipped = PKDict()
        with zipfile.ZipFile(six.BytesIO(zip_bytes), 'r') as z:
            for i in z.infolist():
                b = pykern.pkio.py_path(i.filename).basename
                c = z.read(i)
                if b.lower() == simulation_db.SIMULATION_DATA_FILE:
                    assert not data, \
                        'too many db files {} in archive'.format(b)
                    data = read_json(c, sim_type)
                    continue
                if '__MACOSX' in i.filename:
                    continue
                #TODO(robnagler) ignore identical files hash
                assert not b in zipped, \
                    '{} duplicate file in archive'.format(i.filename)
                zipped[b] = tmp.join(b)
                zipped[b].write(c, 'wb')
        assert data, \
            'missing {} in archive'.format(simulation_db.SIMULATION_DATA_FILE)
        needed = set()
        s = sirepo.sim_data.get_class(data.simulationType)
        for n in s.lib_file_basenames(data):
#TODO(robnagler) this does not allow overwrites of lib files,
# but it needs to be modularized
            if s.lib_file_exists(n):
                continue
#TODO(robnagler) raise useralert instead of an assert
            assert n in zipped, \
                'auxiliary file={} missing in archive'.format(n)
            needed.add(n)
        for b, src in zipped.items():
            if b in needed:
                src.copy(s.lib_file_write_path(b))
        return data
