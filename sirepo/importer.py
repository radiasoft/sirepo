# -*- coding: utf-8 -*-
u"""Import a single archive simulation

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import py.path
import zipfile


def read_json(text, template):
    """Read json file and return

    Args:
        text (IO): file to be read
        template (module): expected type

    Returns:
        dict: data
    """
    from sirepo import simulation_db

    # attempt to decode the input as json first, if invalid try python
    data = simulation_db.json_load(text)
    assert data.simulationType == template.SIM_TYPE, \
        'simulationType {} invalid, expecting {}'.format(
            data.simulationType,
            template.SIM_TYPE,
        )
    return data


def read_zip(stream, template):
    """Read zip file and store contents

    Args:
        stream (IO): file to read
        template (module): expected app

    Returns:
        dict: data
    """
    from sirepo import simulation_db
    from pykern import pkcollections

    tmp = simulation_db.tmp_dir()
    data = None
    zipped = pkcollections.Dict()
    with zipfile.ZipFile(stream, 'r') as z:
        for i in z.infolist():
            b = py.path.local(i.filename).basename
            c = z.read(i)
            if b.lower() == simulation_db.SIMULATION_DATA_FILE:
                assert not data, \
                    'too many db files {} in archive'.format(b)
                data = read_json(c, template)
                continue
            assert not b in zipped, \
                '{} duplicate file in archive'.format(i.filename)
            fn = tmp.join(b)
            with open(str(fn), 'wb') as f:
                f.write(c)
            zipped[b] = fn
    assert data, \
        'missing {} in archive'.format(simulation_db.SIMULATION_DATA_FILE)
    lib_d = simulation_db.simulation_lib_dir(template.SIM_TYPE)
    needed = template.lib_files(data, lib_d)
    for n in needed:
        assert n.basename in zipped or n.check(file=True, exists=True), \
            'auxiliary file {} missing in archive'.format(n.basename)
    for b, src in zipped.items():
        src.copy(lib_d)
    return data
