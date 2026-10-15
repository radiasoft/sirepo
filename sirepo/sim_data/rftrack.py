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
        """Read the rslume.rftrack HDF5 archive (`RFTrackSimulator.archive()`)
        and build the full imported sirepo data right here, on the API
        server -- not in `stateful_compute_import_file`
        (sirepo.template.rftrack), which runs in the job agent instead.

        The import writes new lib files -- the bunch (a "fromFile"
        `beam.distributionFile`) and any CAVITY/SOLENOID with a baked field
        array instead of a file reference -- which needs a real `qcall`
        the job agent doesn't have. Same reason radia.py's own binary
        import writes its DMP file here. `stateful_compute_import_file` is
        then a trivial passthrough, which only has to exist because
        api_importFile's dispatch requires it for any import that isn't
        .json/.zip.
        """
        import rslume.rftrack_archive
        import sirepo.template.rftrack
        import tempfile

        res = cls._prepare_import_file_name_args(req)
        with tempfile.NamedTemporaryFile(suffix=".h5") as t:
            t.write(req.form_file.as_bytes())
            t.flush()
            a = rslume.rftrack_archive.read_archive(t.name)
        return res.pkupdate(
            imported_data=sirepo.template.rftrack.build_imported_data(
                a, res.purebasename, qcall=req.qcall
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
