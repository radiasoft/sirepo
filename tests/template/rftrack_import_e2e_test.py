"""PyTest for a real browser-facing /importFile POST for rftrack.

Regression test for a bug none of the other rftrack_import_*_test.py
files can catch: they all call `stateful_compute_import_file()` (or
`srunit.template_import_file()`, which just calls it directly too)
in-process, bypassing `sirepo.server`'s `api_importFile` entirely. That
handler unwraps this call's result as `resp.content_as_object()
.imported_data` -- a plain, unwrapped return value (which worked fine in
every direct call) makes it find no such key, fail, and fall back to
returning the raw, *unsaved* stateful-compute reply -- skipping the save
that normally assigns `models.simulation.simulationId`. The browser hit
exactly this after a real import: it reached the post-import redirect
with no simulationId to redirect to, and the JS could not serialize
`undefined`.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_basic(fc):
    from pykern import pkunit
    from pykern.pkunit import pkeq, pkok
    from pykern.pkcollections import PKDict

    fc.sr_get_root("rftrack")
    res = fc.sr_post_form(
        "importFile",
        PKDict(folder="/importer_test"),
        PKDict(simulation_type="rftrack"),
        file=pkunit.data_dir().join("basic.py"),
    )
    pkok(
        res.pkunchecked_nested_get("models.simulation.simulationId"),
        "no simulationId in res={}",
        res,
    )
    pkeq("/importer_test", res.models.simulation.folder)
    # sorted by type (see rftrack_import_test.py's test_basic for why)
    pkeq(
        ["C1", "D1", "Q1", "Q2", "SCR1"],
        [e.name for e in res.models.elements],
    )


def test_lib_file_already_exists(fc):
    """A field-map file already in rftrack's lib store before the
    import even starts (e.g. uploaded for an earlier sim, or re-
    importing the same script twice) is never "missing" to the generic
    lattice import dialog's upload prompt -- it only prompts for a file
    not already in the lib list, so without stateful_compute_import_
    file() checking for this itself (see rftrack.py's _lib_file_data()),
    `l` would stay at the "not recoverable" placeholder forever, even
    though the real file was sitting there the whole time.
    """
    from pykern import pkunit
    from pykern.pkunit import pkeq
    from pykern.pkcollections import PKDict

    fc.sr_get_root("rftrack")
    fc.sr_post_form(
        "uploadLibFile",
        params=PKDict(
            simulation_type="rftrack",
            simulation_id="NONSIMID",
            file_type="CAVITY-fieldMapFile",
        ),
        data=PKDict(),
        file=pkunit.data_dir().join("rf_gunG4.dat"),
    )
    res = fc.sr_post_form(
        "importFile",
        PKDict(folder="/importer_test"),
        PKDict(simulation_type="rftrack"),
        file=pkunit.data_dir().join("cavity_fieldmap.py"),
    )
    gun = {e.name: e for e in res.models.elements}["gunG4"]
    pkeq("rf_gunG4.dat", gun.fieldMapFile)
    # the real file's own s range (0.0 to 2.5), not the "file missing"
    # placeholder's fabricated 1.0 or the "not recoverable" 0
    pkeq(2.5, round(gun.l, 6))
    # rescaleMode/maxField are recovered too, assuming a CAVITY used
    # "peak" mode (see rftrack_import_recorder._resolve_rescale()) --
    # unlike l, this doesn't actually depend on the file being found
    pkeq("peak", gun.rescaleMode)
    pkeq(20.0, gun.maxField)


def test_validate_file_updates_length_after_upload(fc):
    """The other half of the fix above: a field-map file genuinely
    missing at import time (so `l` comes back `0`, same as
    `rftrack_import_test.py`'s `test_awa_zone1_without_data_files`) can
    still be corrected afterward, once the user actually uploads it
    through the generic lattice import dialog's "missing files" prompt
    -- rftrack.py's validate_file() recomputes `l` for every element
    referencing it and saves the sim, the one piece `_lib_file_data()`
    can't reach since no file existed anywhere for it to find at import
    time.
    """
    from pykern import pkunit
    from pykern.pkunit import pkeq
    from pykern.pkcollections import PKDict

    # a different filename than test_lib_file_already_exists's own
    # "rf_gunG4.dat" -- that test's upload persists in the shared lib
    # store for the rest of this file's test run, so reusing its name
    # here would make this import find the file already there too,
    # defeating the "genuinely missing" setup this test needs
    fc.sr_get_root("rftrack")
    res = fc.sr_post_form(
        "importFile",
        PKDict(folder="/importer_test"),
        PKDict(simulation_type="rftrack"),
        file=pkunit.data_dir().join("cavity_fieldmap2.py"),
    )
    sim_id = res.models.simulation.simulationId
    gun = {e.name: e for e in res.models.elements}["gunG4"]
    pkeq(0, gun.l)
    # unlike l, maxField doesn't need the file to be found at all (see
    # rftrack_import_recorder._resolve_rescale())
    pkeq(20.0, gun.maxField)

    fc.sr_post_form(
        "uploadLibFile",
        params=PKDict(
            simulation_type="rftrack",
            simulation_id=sim_id,
            file_type="CAVITY-fieldMapFile",
        ),
        data=PKDict(),
        file=pkunit.data_dir().join("rf_gun2.dat"),
    )
    updated = fc.sr_get_json(
        "simulationData",
        PKDict(simulation_type="rftrack", simulation_id=sim_id, pretty="0"),
    )
    gun = {e.name: e for e in updated.models.elements}["gunG4"]
    pkeq(2.5, round(gun.l, 6))
    pkeq("peak", gun.rescaleMode)
    pkeq(20.0, gun.maxField)
