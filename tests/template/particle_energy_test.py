# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.template_common.ParticleEnergy`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkunit import pkeq
import pytest

def test_energy_conversion():
    from sirepo.template.template_common import ParticleEnergy
    energy = PKDict(
        pc=0.2997948399999999,
    )
    ParticleEnergy.compute_energy('madx', 'proton', energy)
    pkeq(energy, PKDict(
        beta=0.3043592432062238,
        brho=1.0000079454967472,
        energy=0.9850032377589688,
        gamma=1.0498055888568685,
        kinetic_energy=0.04673119175896878,
        pc=0.2997948399999999,
    ))
    for f in energy:
        if f == 'kinetic_energy':
            continue
        pkeq(energy, ParticleEnergy.compute_energy('madx', 'proton', PKDict({
            f: energy[f],
        })))


def test_energy_conversion_by_sim_type():
    from sirepo.template.template_common import ParticleEnergy
    energy = PKDict(
        pc=1.001,
        gamma=1761.257,
    )
    pkeq(
        ParticleEnergy.compute_energy('madx', 'electron', energy.copy()),
        PKDict(
            beta=0.999999869700802,
            brho=3.33897659310099,
            energy=1.0010001304797258,
            gamma=1958.908474421938,
            kinetic_energy=1.0004891315517257,
            pc=1.001,
        )
    )
    pkeq(
        ParticleEnergy.compute_energy('opal', 'electron', energy.copy()),
        PKDict(
            beta=0.999999838815018,
            brho=3.002077837014637,
            energy=0.900000438932496,
            gamma=1761.257,
            kinetic_energy=0.899489440004496,
            pc=0.9000002938659415,
        )
    )
