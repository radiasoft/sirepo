# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.srw_importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_srw_1(fc):
    _t(
        {
            "amx": ("amx", None),
            "amx_bl2": ("amx", "--op_BL=2"),
            "amx_bl3": ("amx", "--op_BL=3"),
            "amx_bl4": ("amx", "--op_BL=4"),
            "chx": ("chx", None),
            "chx_fiber": ("chx_fiber", None),
            "exported_chx": ("exported_chx", None),
            "exported_gaussian_beam": ("exported_gaussian_beam", None),
            "exported_undulator_radiation": ("exported_undulator_radiation", None),
            "lcls_simplified": ("lcls_simplified", None),
            "lcls_sxr": ("lcls_sxr", None),
        },
        fc,
    )


def test_srw_2(fc):
    _t(
        {
            "nsls-ii-esm-beamline": ("nsls-ii-esm-beamline", None),
            "sample_from_image": ("sample_from_image", None),
            "smi_es1_bump_norm": ("smi", "--beamline ES1 --bump --BMmode Norm"),
            "smi_es1_nobump": ("smi", "--beamline ES1"),
            "smi_es2_bump_lowdiv": ("smi", "--beamline ES2 --bump --BMmode LowDiv"),
            "smi_es2_bump_norm": ("smi", "--beamline ES2 --bump --BMmode Norm"),
            "srx": ("srx", None),
            "srx_bl2": ("srx", "--op_BL=2"),
            "srx_bl3": ("srx", "--op_BL=3"),
            "srx_bl4": ("srx", "--op_BL=4"),
        },
        fc,
    )


def _t(tests, fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp
    from pykern.pkcollections import PKDict

    with pkunit.save_chdir_work(want_empty=False):
        for b in sorted(tests.keys()):
            fc.sr_get_root("srw")
            res = fc.sr_post_form(
                "importFile",
                PKDict(folder="/srw_import_test"),
                PKDict(simulation_type="srw"),
                file=pkunit.data_dir().join(f"{tests[b][0]}.py"),
            )
            res["version"] = "IGNORE-VALUE"
            pkunit.assert_object_with_json(b, res)
