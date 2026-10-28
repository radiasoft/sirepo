"""PyTest for :class:`sirepo.template.opal.OpalMadxConverter`, which
writes lib files, so needs a user. Separate from madx_converter_test.py,
whose save_chdir_work() calls remove the auth db, created once per process.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_opal_from_madx_and_back():
    from pykern import pkio
    from pykern import pkunit
    from sirepo import srunit
    from sirepo.template import opal
    from sirepo.template.opal import OpalMadxConverter

    with srunit.quest_start(want_user=True) as qcall:
        data = OpalMadxConverter(qcall=qcall).from_madx_text(
            pkio.read_text(pkunit.data_dir().join("opal_from_madx.madx"))
        )
        pkunit.file_eq(
            "opal_from_madx.in",
            actual=opal.python_source_for_model(data, model=None, qcall=qcall),
        )
        # RFCAVITY's generated field map
        pkunit.pkre(
            r"^1DDynamic 521\n0 50 1301\n1300\n",
            opal._SIM_DATA.lib_file_read_text(
                "RFCAVITY-fmapfn.madx-rfcavity-0.5m-1300MHz.txt",
                qcall=qcall,
            ),
        )
        pkunit.file_eq(
            "opal_to_madx.madx",
            actual=OpalMadxConverter(qcall=qcall).to_madx_text(data),
        )
