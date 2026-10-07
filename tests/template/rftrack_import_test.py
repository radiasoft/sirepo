"""PyTest for rftrack's stateful_compute_import_file

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

#: the 6 unique field-map data files awa_zone1.py references, by the
#: exact (lib-file-prefixed) name it passes to numpy.loadtxt() -- real
#: AWA field maps are tens of KB each and don't belong in this repo, so
#: the fixtures alongside the script are tiny stubs (same 5 rows for all
#: 6) good enough to be loadable and non-degenerate (a nonzero peak), not
#: to be physically meaningful
_AWA_ZONE1_DATA_FILES = (
    "CAVITY-fieldMapFile.linac.dat",
    "CAVITY-fieldMapFile.rf_gunG4.dat",
    "SOLENOID-fieldMapFile.sol_bucking-focusing_pm550A.dat",
    "SOLENOID-fieldMapFile.sol_linac_500A.dat",
    "SOLENOID-fieldMapFile.sol_linacLB_500A.dat",
    "SOLENOID-fieldMapFile.sol_matching_m440A.dat",
)


def test_awa_zone1_round_trip():
    """Export the real "AWA Zone 1 matching notebook" sim
    (awa_zone1-original.json, a verbatim copy of that production sim's
    own sirepo-data.json) to Python exactly as a user would from the UI,
    then import that export right back in, and compare the two
    sirepo-data.json structures -- the same comparison the user did by
    hand that found the length-fabrication bug fixed just before this
    test was written.

    Goes through the real `python_source_for_model()` -> `stateful_
    compute_import_file()` pair, not the lower-level runner/mapper calls
    the other two awa_zone1 tests use, and -- like the real browser
    workflow this is modeled on -- provides no companion data files at
    all. `l` is still expected back as this plan's own documented
    placeholder (0), since it's genuinely derived from the file's own
    content -- but rescaleMode/maxField/scaleFactor are *not*: the
    generated script bakes them in as literal values applied uniformly
    to whatever array numpy.loadtxt() returns, real or (as here) the
    missing-file stub, so they round-trip exactly either way (see
    rftrack_import_recorder._resolve_rescale(); the per-element-type
    assumption it relies on -- CAVITY used "peak", SOLENOID used
    "factor" -- can't be verified, but matches every real sim seen so
    far). Everything else (names, types, positions, misalignment,
    apertures, frequencies, phases, file*names*, and the cathode bunch)
    is expected to round-trip exactly too.
    """
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    import pykern.pkjson
    from sirepo.template import rftrack

    original = pykern.pkjson.load_any(pkunit.data_dir().join("awa_zone1-original.json"))
    original.report = "animation"
    script = rftrack.python_source_for_model(original, model=None, qcall=None)
    imported = rftrack.stateful_compute_import_file(
        data=PKDict(
            args=PKDict(
                basename="awa_zone1.py",
                purebasename="awa_zone1",
                ext_lower=".py",
                file_as_str=script,
            )
        )
    ).imported_data

    o_by_name = {e.name: e for e in original.models.elements}
    i_by_name = {e.name: e for e in imported.models.elements}
    pkeq(set(o_by_name), set(i_by_name))

    # fields with no dependency on the missing field-map file content:
    # these are expected to round-trip exactly
    for name, o in o_by_name.items():
        i = i_by_name[name]
        pkeq(o.type, i.type, "name={}", name)
        for f in ("aperture_x", "aperture_y", "dx", "dy", "dz", "rx", "ry", "rz"):
            pkeq(o[f], i[f], "name={} field={}", name, f)
        if o.type == "CAVITY":
            pkeq(o.fieldSource, i.fieldSource, "name={}", name)
            pkeq(o.frequency, i.frequency, "name={}", name)
            pkeq(o.phase, i.phase, "name={}", name)
        if o.get("fieldSource") == "fieldMap":
            # the filename is recovered from the script's own
            # numpy.loadtxt() call, independent of whether that file
            # actually exists -- unlike the fields excluded below, which
            # the script only ever computes *from* that file's content
            pkeq(o.fieldMapFile, i.fieldMapFile, "name={}", name)

    o_by_id = {e._id: e.name for e in original.models.elements}
    i_by_id = {e._id: e.name for e in imported.models.elements}
    # physical order/position is fully recoverable regardless of the
    # field-map files -- Volume.add()'s own args carry it, not anything
    # read back from the file they reference
    pkeq(
        [o_by_id[i] for i in original.models.beamlines[0]["items"]],
        [i_by_id[i] for i in imported.models.beamlines[0]["items"]],
    )
    pkeq(
        [p.elemedge for p in original.models.beamlines[0].positions],
        [p.elemedge for p in imported.models.beamlines[0].positions],
    )

    pkeq(
        original.models.simulation.elementPosition,
        imported.models.simulation.elementPosition,
    )

    ob, ib = original.models.beam, imported.models.beam
    pkeq(ob.particle, ib.particle)
    pkeq(ob.distributionType, ib.distributionType)
    # recovered straight from the generated script's own BUNCH global,
    # not from any RF_Track call -- pc has no execution trace at all for
    # a Cathode bunch (see rftrack_import_driver._resolve_pc_mev())
    pkeq(ob.pc, ib.pc)
    pkeq(ob.charge_nC, ib.charge_nC)
    pkeq(ob.np, ib.np)
    pkeq(ob.cutoffT, ib.cutoffT)
    pkeq(ob.cutoffX, ib.cutoffX)
    pkeq(ob.cutoffY, ib.cutoffY)
    pkeq(ob.ePhoton, ib.ePhoton)
    pkeq(ob.flatTopLength, ib.flatTopLength)
    pkeq(ob.noiseReduc, ib.noiseReduc)
    pkeq(ob.phiEff, ib.phiEff)
    pkeq(ob.riseTime, ib.riseTime)
    pkeq(ob.sigX, ib.sigX)

    # documented limitation (see rftrack-import-plan.md): l is only ever
    # computed from the file's own content, with no file provided here
    for name, i in i_by_name.items():
        if i.get("fieldSource") == "fieldMap":
            o = o_by_name[name]
            pkeq(0, i.l, "name={}", name)
            pkeq(o.rescaleMode, i.rescaleMode, "name={}", name)
            pkeq(o.scaleFactor, i.scaleFactor, "name={}", name)
            pkeq(o.maxField, i.maxField, "name={}", name)
    # 12 field-map warnings, plus one more: track() is a no-op now (see
    # rftrack_import_recorder._NOOP_METHODS), so the generated script's
    # own main() keeps running past it -- straight into
    # save_particles("final_particles.npy", tracked, ...), which crashes
    # since `tracked` is None (the no-op's return value) -- tolerated
    # as a partial-run warning (see rftrack_import_driver.main()), not a
    # failure, since everything this import wants was already captured
    # by the time that happens
    pkeq(13, len(imported.importWarnings))
    pkeq(
        True,
        any("did not finish running" in w for w in imported.importWarnings),
    )


def test_awa_zone1_with_stub_data_files():
    """End-to-end regression test for a real production export (the "AWA
    Zone 1 matching notebook" sim) hitting three bugs in one session: a
    missing field-map file crashing the import outright, the same
    missing file not being requested the way other lattice-code importers
    already do, and the script's own autophase()/track() calls (always
    present, at the very end of every real exported script's main())
    timing out instead of being skipped. Stub (not real) data files let
    this also exercise the "the file actually exists" path for every
    field map, not just "missing" (see test_awa_zone1_without_data_files)
    -- including rescaleMode/maxField/scaleFactor recovery (see
    rftrack_import_recorder._resolve_rescale()), even though that part
    doesn't actually need the file to be real either.

    Goes through rftrack_import_runner/rftrack_import_mapper directly,
    not stateful_compute_import_file: srunit.template_import_file() (used
    by test_basic) has no way to seed a script's companion data files
    into its scratch directory alongside it.
    """
    from pykern import pkunit
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    script = pkunit.data_dir().join("awa_zone1.py").read_text("utf8")
    data_files = {
        n: pkunit.data_dir().join(n).read_text("utf8") for n in _AWA_ZONE1_DATA_FILES
    }
    res = rftrack_import_runner.run(script, data_files=data_files)
    pkeq("ok", res.status)
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    # none: the file is found, and rescaleMode/scaleFactor/maxField are
    # now recovered too (see rftrack_import_mapper_test.py)
    pkeq([], warnings)
    pkeq("absolute", element_position)
    pkeq(
        [
            "Gun",
            "SolBF",
            "SolM",
            "L1",
            "SolL1",
            "YAG1",
            "L2",
            "SolL2",
            "L3",
            "YAG2",
            "SolL4",
            "L4",
            "L5",
            "YAG3",
            "L6",
            "YAG4",
        ],
        [x.name for x in e],
    )
    pkeq(
        [
            "CAVITY",
            "SOLENOID",
            "SOLENOID",
            "CAVITY",
            "SOLENOID",
            "SCREEN",
            "CAVITY",
            "SOLENOID",
            "CAVITY",
            "SCREEN",
            "SOLENOID",
            "CAVITY",
            "CAVITY",
            "SCREEN",
            "CAVITY",
            "SCREEN",
        ],
        [x.type for x in e],
    )
    gun = e[0]
    pkeq("fieldMap", gun.fieldSource)
    pkeq("rf_gunG4.dat", gun.fieldMapFile)
    pkeq(1300000000, gun.frequency)
    pkeq(0.0, gun.elemedge)
    pkeq("peak", gun.rescaleMode)
    pkeq(80.0, gun.maxField)
    sol_bf = e[1]
    pkeq("sol_bucking-focusing_pm550A.dat", sol_bf.fieldMapFile)
    pkeq(-0.5, sol_bf.elemedge)
    pkeq("factor", sol_bf.rescaleMode)
    pkeq(0.0001, sol_bf.scaleFactor)
    l1 = e[3]
    pkeq("linac.dat", l1.fieldMapFile)
    pkeq(0.576433, l1.elemedge)
    pkeq("peak", l1.rescaleMode)
    pkeq(22.0, l1.maxField)
    pkeq("SCREEN", e[5].type)
    pkeq("YAG1", e[5].name)

    b = rftrack_import_mapper.map_bunch(res.calls)
    pkeq("electron", b.particle)
    pkeq(1, b.charge_nC)
    pkeq(10000, b.np)


def test_awa_zone1_without_data_files():
    """Same script, no data files provided at all -- the exact scenario
    that originally crashed (reported with the real sim): every one of
    the 12 field-map elements (6 unique files, several reused -- all six
    L1-L6 cavities share the same linac.dat) should come back with its
    own warning naming it and the file it needs, not a crash or a
    timeout. The 4 screens need no field map, so warn about nothing.
    """
    from pykern import pkunit
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_mapper, rftrack_import_runner

    script = pkunit.data_dir().join("awa_zone1.py").read_text("utf8")
    res = rftrack_import_runner.run(script)
    pkeq("ok", res.status)
    e, element_position, warnings = rftrack_import_mapper.map_elements(res.calls)
    pkeq(16, len(e))
    pkeq(12, len(warnings))
    # recovered from the script's own numpy.loadtxt() call even though
    # the file itself was never actually present -- only an element with
    # no preceding loadtxt() at all (not the case here) gets back ""
    pkeq("rf_gunG4.dat", e[0].fieldMapFile)
    pkeq(True, all("needs" in w and "uploaded" in w for w in warnings))
    # also recovered despite the missing file: the generated script
    # applies rescaleMode/scaleFactor/maxField as a literal, uniform
    # scalar multiply of whatever array numpy.loadtxt() returns, real or
    # (as here) the missing-file placeholder -- see
    # rftrack_import_recorder._resolve_rescale()
    pkeq("peak", e[0].rescaleMode)
    pkeq(80.0, e[0].maxField)
    pkeq("factor", e[1].rescaleMode)
    pkeq(0.0001, e[1].scaleFactor)


def test_basic():
    from pykern.pkunit import pkeq
    from pykern import pkunit
    from sirepo import srunit

    res = srunit.template_import_file(
        "rftrack", pkunit.data_dir().join("basic.py")
    ).imported_data
    pkeq(None, res.get("importWarnings"))
    pkeq("basic", res.models.simulation.name)
    pkeq("absolute", res.models.simulation.elementPosition)
    # sorted by type (CORRECTOR, DRIFT, QUADRUPOLE, QUADRUPOLE, SCREEN),
    # not left in physical/beamline order -- sirepo-lattice.js's
    # loadTree() groups same-typed elements by assuming they're already
    # contiguous, and a physical-order list (type interleaved with
    # whatever's next in the beamline) breaks that assumption
    pkeq(
        ["C1", "D1", "Q1", "Q2", "SCR1"],
        [e.name for e in res.models.elements],
    )
    pkeq(
        ["CORRECTOR", "DRIFT", "QUADRUPOLE", "QUADRUPOLE", "SCREEN"],
        [e.type for e in res.models.elements],
    )
    by_name = {e.name: e for e in res.models.elements}
    d1 = by_name["D1"]
    pkeq(1.5, d1.l)
    pkeq(0.02, d1.aperture_x)
    pkeq("_ELEMENT", d1._super)

    q1 = by_name["Q1"]
    pkeq("k1", q1.strengthType)
    pkeq(3.0, q1.k1)

    q2 = by_name["Q2"]
    pkeq("gradient", q2.strengthType)
    pkeq(5.0, q2.gradient)

    pkeq(1, len(res.models.beamlines))
    b = res.models.beamlines[0]
    by_id = {e._id: e for e in res.models.elements}
    # beamlines[].items/positions carry the actual (physical) beamline
    # order, independent of how models.elements itself is sorted
    pkeq(
        ["D1", "Q1", "Q2", "C1", "SCR1"],
        [by_id[i].name for i in b["items"]],
    )
    pkeq(
        [0.0, 1.5, 1.8, 2.1, 2.5],
        [p.elemedge for p in b.positions],
    )
    pkeq(b.id, res.models.simulation.activeBeamlineId)
    pkeq(b.id, res.models.simulation.visualizationBeamlineId)

    pkeq("electron", res.models.beam.particle)
    pkeq("cathode", res.models.beam.distributionType)
    pkeq(0.5, res.models.beam.charge_nC)
    pkeq(10000, res.models.beam.np)


def test_wrong_extension():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkexcept
    from sirepo.template import rftrack

    with pkexcept("expecting .py"):
        rftrack.stateful_compute_import_file(
            data=PKDict(args=PKDict(basename="not-python.txt", ext_lower=".txt"))
        )
