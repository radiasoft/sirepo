# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.madx_converter`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_from_elegant_to_madx_and_back():
    from pykern import pkunit
    from pykern.pkunit import pkeq, file_eq
    from sirepo import srunit
    from sirepo.template import elegant
    from sirepo.template.elegant import ElegantMadxConverter

    with pkunit.save_chdir_work() as d:
        for name in (
            "SPEAR3",
            "Compact Storage Ring",
            "Los Alamos Proton Storage Ring",
        ):
            data = _example_data(name)
            with srunit.quest_start() as qcall:
                actual = ElegantMadxConverter(qcall=qcall).to_madx_text(data)
                file_eq(
                    name.lower().replace(" ", "-") + ".madx",
                    actual=actual,
                )
                file_eq(
                    name.lower().replace(" ", "-") + ".lte",
                    actual=elegant.python_source_for_model(
                        ElegantMadxConverter(qcall=qcall).from_madx_text(actual),
                        model=None,
                        qcall=qcall,
                    ),
                )


def test_import_elegant_export_madx():
    from pykern import pkunit, pkdebug
    from pykern.pkcollections import PKDict
    from sirepo import srunit
    from sirepo.template import elegant

    r = srunit.template_import_file("elegant", "test1.ele")
    pkunit.pkeq("needLattice", r.get("importState"))
    data = srunit.template_import_file(
        "elegant",
        "test1.lte",
        arguments=PKDict(eleData=r.eleData),
    ).imported_data
    pkdebug.pkdp(data.models.simulation)
    # this is updated from javascript unfortunately
    data.models.bunch.longitudinalMethod = "3"
    with srunit.quest_start() as qcall:
        actual = elegant.ElegantMadxConverter(qcall=qcall).to_madx_text(data)
        pkunit.file_eq(
            "test1.madx",
            actual=actual,
        )


def test_elegant_from_madx():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkunit import pkeq, file_eq
    from sirepo import srunit
    from sirepo.template import elegant
    from sirepo.template import madx_parser
    from sirepo.template.elegant import ElegantMadxConverter

    # this is updated from javascript unfortunately
    data = madx_parser.parse_file(pkio.read_text(pkunit.data_dir().join("test1.madx")))
    with srunit.quest_start() as qcall:
        actual = ElegantMadxConverter(qcall=qcall).from_madx(data)
        file_eq(
            "test_ele_from_madx.txt",
            actual=elegant.python_source_for_model(actual, model=None, qcall=qcall),
        )


def test_import_opal_export_madx():
    _opal_to_madx("test2")


def test_import_opal_export_madx02():
    _opal_to_madx("test4")


def test_import_opal_export_madx_pow():
    _opal_to_madx("test3")


def _example_data(simulation_name):
    from sirepo import simulation_db
    from sirepo.template import elegant

    for data in simulation_db.examples(elegant.SIM_TYPE):
        if data.models.simulation.name == simulation_name:
            return simulation_db.fixup_old_data(data)[0]
    raise AssertionError(f"failed to find example={simulation_name}")


def _opal_to_madx(basename):
    from pykern import pkunit
    from pykern.pkunit import pkeq, file_eq
    from sirepo import srunit
    from sirepo.template import opal
    from sirepo.template.opal import OpalMadxConverter

    with srunit.quest_start() as qcall:
        file_eq(
            f"{basename}.madx",
            actual=OpalMadxConverter(qcall=qcall).to_madx_text(
                srunit.template_import_file("opal", f"{basename}.in").imported_data,
            ),
        )
