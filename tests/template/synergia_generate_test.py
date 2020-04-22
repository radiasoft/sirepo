# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.synergia`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_generate_python():
    from pykern import pkio
    from pykern import pkunit
    from sirepo.template import synergia
    import re

    with pkunit.save_chdir_work() as d:
        for f in pkio.sorted_glob(pkunit.data_dir().join('*.txt')):
            e = pkio.read_text(f)
            m = re.search(r'^#\s*(.*\S)\s*$', e, flags=re.MULTILINE)
            assert m
            name = m.group(1)
            a = synergia._generate_parameters_file(_example_data(name))
            pkio.write_text(f.basename, a)
            pkunit.pkeq(e, a, 'diff {} {}', f, d.join(f.basename))


def _example_data(name):
    from sirepo import simulation_db
    from sirepo.template import synergia

    for d in simulation_db.examples(synergia.SIM_TYPE):
        if d.models.simulation.name == name:
            return simulation_db.fixup_old_data(d)[0]
    assert False
