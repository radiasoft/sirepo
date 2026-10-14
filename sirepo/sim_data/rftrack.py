# -*- coding: utf-8 -*-
"""rftrack simulation data operations

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["beam"]

    @classmethod
    def prepare_import_file_args(cls, req):
        """Parse the rslume.rftrack HDF5 archive (RFTrackSimulator.
        archive()) and build the full imported sirepo data right here,
        on the API server -- not in `stateful_compute_import_file`
        (sirepo.template.rftrack), which runs in the job agent instead.

        Two things need a brand new lib file written during import, and
        both need a real `qcall` the job agent doesn't have: a CAVITY/
        SOLENOID element with a baked field array (an RF_Track
        RF_FieldMap_1d/Static_Magnetic_FieldMap_1d, not a file
        reference), and the bunch itself, which `archive()` writes as a
        real openPMD particle file sharing the same HDF5 file --
        imported as `beam.distributionFile` ("fromFile" distribution),
        not reconstructed from statistics. Same reason radia.py's own
        binary import writes its one DMP file here instead of in its
        own `stateful_compute_import_file`; this just has potentially
        several files (one per field-map element, one for the bunch)
        instead of one.

        `stateful_compute_import_file` only has to exist at all because
        api_importFile's own dispatch (sirepo/server.py) requires it for
        any import that isn't .json/.zip -- it's a trivial passthrough
        of what this method already built (see its own docstring).
        """
        import h5py
        import sirepo.template.rftrack
        import tempfile

        res = cls._prepare_import_file_name_args(req)
        with tempfile.NamedTemporaryFile(suffix=".h5") as t:
            t.write(req.form_file.as_bytes())
            t.flush()
            with h5py.File(t.name, "r") as f:
                field_maps = f.get("field_maps")

                def _group_to_dict(group):
                    # A field-map array (e.g. RF_FieldMap_1d's "ez",
                    # Static_Magnetic_FieldMap_1d's "bz") is written as
                    # a real HDF5 dataset, not an attr
                    # (rslume.rftrack_archive._write_attrs_h5: "an attr isn't
                    # meant to hold something that size") -- only
                    # reading .attrs silently drops those fields.
                    d = dict(group.attrs)
                    for k in group:
                        d[k] = group[k][()]
                    # Several elements built from the same uploaded
                    # field-map file (e.g. a linac's identical
                    # accelerating cavities) share one copy of the
                    # array, referenced as "@<md5>" instead of each
                    # embedding a byte-for-byte duplicate (see
                    # rslume.rftrack_archive._dedupe_field_maps()) -- resolve
                    # that back into the real array here.
                    if field_maps is not None:
                        for k in list(d.keys()):
                            v = d[k]
                            if isinstance(v, str) and v.startswith("@"):
                                d[k] = field_maps[v[1:]][()]
                    return d

                elements = [
                    _group_to_dict(f["elements"][str(i)])
                    for i in range(len(f["elements"]))
                ]
                beamline_class = str(f.attrs["beamline_class"])
                bunch_type = str(f.attrs["bunch_type"])
                distribution_file, particle_group = (
                    sirepo.template.rftrack.write_distribution_lib_file(
                        f, res.purebasename, qcall=req.qcall
                    )
                )
                # autophase is always written by archive() (inferred
                # from the elements' own t0 state if not passed
                # explicitly -- see rslume.rftrack_archive._infer_autophase),
                # so a plain cavity `phase` (its archived phid, nothing
                # folded in) plus this flag is enough for the generated
                # script's own existing autophase(volume) to correctly
                # re-derive each cavity's (and Screen's) real t0 on
                # import, exactly reproducing the archived physics --
                # same deterministic search that produced it in the
                # first place.
                autophase = bool(f.attrs.get("autophase", 0))
                space_charge = None
                if "space_charge" in f:
                    sc = f["space_charge"]
                    space_charge = dict(sc.attrs)
                    if "grid" in space_charge:
                        space_charge["grid"] = tuple(int(n) for n in space_charge["grid"])
        return res.pkupdate(
            imported_data=sirepo.template.rftrack.build_imported_data(
                elements,
                beamline_class,
                bunch_type,
                particle_group,
                distribution_file,
                res.purebasename,
                autophase,
                space_charge,
                qcall=req.qcall,
            ),
        )

    @classmethod
    def _lib_file_basenames(cls, data):
        # LatticeSimData._lib_file_basenames() only scans lattice elements
        # (CAVITY/SOLENOID field maps) for InputFile fields; beam.
        # distributionFile lives on a different (non-element) model, so it
        # has to be added explicitly or the file never gets copied into the
        # run directory.
        res = super()._lib_file_basenames(data)
        b = data.models.beam
        if b.distributionType == "fromFile" and b.distributionFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "beam", "distributionFile", b.distributionFile
                )
            )
        return res

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        cls._init_models(
            data.models,
            (
                "beam",
                "beamline",
                "simulation",
                "simulationSettings",
                "simulationStatus",
                "statAnimation",
            ),
        )
        if not data.models.beam.get("randomSeed"):
            # randomSeed was briefly an OptionalInteger (default "") before
            # becoming a required Integer defaulting to RF_Track's own
            # mt19937 default seed (5489, see rftrack.py); _init_models()
            # only backfills missing keys, not an already-saved "".
            data.models.beam.randomSeed = 5489
