# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_create_zip(fc):
    from pykern import pkio
    from pykern import pkunit
    from pykern import pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern.pkunit import pkeq
    from sirepo import srunit
    import re
    import zipfile

    imported = _import(fc)
    for sim_type, sim_name, expect in imported + [
        ('elegant', 'bunchComp - fourDipoleCSR', ['WAKE-inputfile.knsl45.liwake.sdds', 'run.py', 'sirepo-data.json']),
        ('srw', 'Tabulated Undulator Example', ['magnetic_measurements.zip', 'run.py', 'sirepo-data.json']),
        ('warppba', 'Laser Pulse', ['run.py', 'sirepo-data.json']),
    ]:
        sim_id = fc.sr_sim_data(sim_name, sim_type)['models']['simulation']['simulationId']
        with pkio.save_chdir(pkunit.work_dir()) as d:
            for t in 'zip', 'html':
                r = fc.sr_get(
                    'exportArchive',
                    PKDict(
                        simulation_type=sim_type,
                        simulation_id=sim_id,
                        filename='anything.' + t,
                    )
                )
                p = d.join(sim_name + '.' + t)
                x = pkcompat.from_bytes(r.data)
                if t == 'html':
                    m = re.search(r'name="zip" \S+ value="([^"]+)"', x, flags=re.DOTALL)
                    x = m.group(1).decode('base64')
                p.write(x, mode='wb')
                e = expect
                if t == 'html':
                    e.remove('run.py')
                pkeq(
                    e,
                    sorted(zipfile.ZipFile(str(p)).namelist()),
                )


def _import(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern import pkio
    from pykern import pkunit
    import zipfile

    res = []
    for f in pkio.sorted_glob(pkunit.data_dir().join('*.zip')):
        with zipfile.ZipFile(str(f)) as z:
            expect = sorted(z.namelist() + ['run.py'])
        d = fc.sr_post_form(
            'importFile',
            PKDict(folder='/exporter_test'),
            PKDict(simulation_type=f.basename.split('_')[0]),
            file=f,
        )
        res.append((d.simulationType, d.models.simulation.name, expect))
    return res
