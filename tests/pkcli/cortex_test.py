"""Test pkcli.cortex

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_convert_ao_to_wo():
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
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
    pkio.write_text(
        pkunit.work_dir().join("convert_ao_to_wo.ndiff"),
        "".join(
            f"{e} {v.target_pct!r} {v.min_pct!r} {v.max_pct!r}\n" for e, v in c.items()
        ),
    )
    pkunit.file_eq(pkunit.data_dir().join("convert_ao_to_wo.ndiff"))
