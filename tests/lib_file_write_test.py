"""Test lib_file_write containment

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_lib_file_write_containment():
    from pykern import pkio, pkunit
    from sirepo import srdb, srunit, util
    import sirepo.sim_data
    import sirepo.template.rftrack

    pkio.unchecked_remove(srdb.root())
    with srunit.quest_start() as qcall:
        qcall.cookie.set_sentinel()
        try:
            qcall.auth.login(method="guest", sim_type="rftrack")
        except util.SReplyExc:
            pass
        sd = sirepo.sim_data.get_class("rftrack")
        sd.lib_file_write("ok.dat", "x", qcall=qcall)
        with pytest.raises(AssertionError):
            sd.lib_file_write("a.../../../escape.dat", "x", qcall=qcall)
        with pytest.raises(AssertionError):
            sd.lib_file_read_binary("a.../../../escape.dat", qcall=qcall)
        # untrusted element name from an imported archive
        b = sirepo.template.rftrack._write_field_map_lib_file(
            "CAVITY", "fieldMapFile", "../../../../escape", "1 2\n", qcall, {}
        )
        pkunit.pkok("/" not in b and ".." not in b, "unsafe basename={}", b)
        pkunit.pkok(
            sd.lib_file_exists(
                sd.lib_file_name_with_model_field("CAVITY", "fieldMapFile", b),
                qcall=qcall,
            ),
            "expecting file in lib dir",
        )
