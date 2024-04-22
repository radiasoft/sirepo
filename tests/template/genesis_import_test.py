"""PyTest for :mod:`sirepo.template.zgoubi_importer`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_lib_file_list(fc):
    from pykern import pkio, pkjson, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
    import re

    fc.sr_get_root()
    r = fc.sr_post_form(
        "importFile",
        PKDict(folder="/importer_test"),
        PKDict(simulation_type=fc.sr_sim_type),
        # NOTE: first file must be first
        file=pkunit.data_dir().join("test.in"),
    )
    pkunit.pkok(r.get("missingFiles"), "expecting missingFiles reply={}", r)
    r = fc.sr_post_form(
        "uploadLibFile",
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id="NONSIMID",
            file_type=r.missingFiles[0].file_type,
        ),
        data=PKDict(),
        file=pkunit.data_dir().join("mag-test.in"),
    )
    pkunit.pkok(not r.get("error"), "not expecting error={}", r)
    r = fc.sr_post_form(
        "importFile",
        PKDict(folder="/importer_test"),
        PKDict(simulation_type=fc.sr_sim_type),
        # NOTE: first file must be first
        file=pkunit.data_dir().join("test.in"),
    )
    pkunit.pkok(r.get("models"), "expecting models reply={}", r)
