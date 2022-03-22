# -*- coding: utf-8 -*-
u"""Test for :mod:`sirepo.sim_data.controls.AmpConverter`

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

def test_amp_converter():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.sim_data.controls import AmpConverter

    def _amp_converter(table):
        return AmpConverter(
            PKDict(
                particle='proton',
                gamma=5.32894486339626,
            ),
            table,
        )

    def _eq(v1, v2):
        pkeq(_rounded(v1), _rounded(v2))

    def _rounded(v):
        return f'{v:0.5f}'

    def _test_cases(ac, currents):
        k = [0.288217, 1.46403, -1.46403, 2.74173]
        for i in (range(len(k))):
            _eq(currents[i], ac.kick_to_current(k[i]))
            _eq(k[i], ac.current_to_kick(currents[i]))

    _test_cases(
        _amp_converter([
            [-2392.17, 0.0149716],
            [-2192.7, 0.0156032],
            [-1993.16, 0.0161872],
            [-1793.79, 0.0166792],
            [-1594.25, 0.016992],
            [-1394.92, 0.0171348],
            [-1195.6, 0.0172024],
            [-996.32, 0.0172456],
            [-796.85, 0.0172716],
            [796.85, 0.0172716],
            [996.32, 0.0172456],
            [1195.6, 0.0172024],
            [1394.92, 0.0171348],
            [1594.25, 0.016992],
            [1793.79, 0.0166792],
            [1993.16, 0.0161872],
            [2192.7, 0.0156032],
            [2392.17, 0.0149716],
        ]),
        [273.3705832969527, 1400.002276897038, -1400.002276897038, 2999.999802894563],
    )

    _test_cases(
        _amp_converter(None),
        [0.04721547366471649, 0.2398361994932807, -0.2398361994932807, 0.449148],
    )

    _test_cases(
        _amp_converter(
            [
                [0.5, 0.03],
            ],
        ),
        [157.38491221572164, 799.4539983109357, -799.4539983109357, 1497.15990],
    )
