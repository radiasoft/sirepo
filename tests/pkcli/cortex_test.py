"""Test pkcli.cortex

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_convert_ao_to_wo():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.pkcli import cortex

    c = cortex._convert_ao_to_wo(
        PKDict(
            m=PKDict(
                is_atom_pct=True,
                components=PKDict(
                    Fe=PKDict(target_pct=70.0, min_pct=65.0, max_pct=75.0),
                    Cr=PKDict(target_pct=20.0, min_pct=18.0, max_pct=22.0),
                    Ni58=PKDict(target_pct=9.0, min_pct=8.0, max_pct=10.0),
                    C=PKDict(target_pct=1.0, min_pct=None, max_pct=1.5),
                    # target_pct=0 previously raised ZeroDivisionError
                    Mn=PKDict(target_pct=0.0, min_pct=0.0, max_pct=1.0),
                ),
            ),
        ),
    ).m.components
    for e, v in PKDict(
        Fe=(71.302354858, 66.209329511, 76.395380205),
        Cr=(18.967995584, 17.071196026, 20.864795142),
        Ni58=(9.510569044, 8.453839150, 10.567298937),
        C=(0.219080514, None, 0.219080514),
        Mn=(0.0, 0.0, 1.002059723),
    ).items():
        pkeq(
            v,
            tuple(
                None if x is None else round(x, 9)
                for x in (c[e].target_pct, c[e].min_pct, c[e].max_pct)
            ),
        )
