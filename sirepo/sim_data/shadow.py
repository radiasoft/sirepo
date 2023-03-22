# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkconfig
from pykern import pkjson
import sirepo.sim_data
import scipy.constants
import hashlib


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(("colorMap", "notes", "aspectRatio"))

    @classmethod
    def compute_job_hash(cls, data, qcall):
        """Hash fields related to data and set computeJobHash

        Only needs to be unique relative to the report, not globally unique
        so MD5 is adequate. Long and cryptographic hashes make the
        cache checks slower.

        Args:
            data (dict): simulation data
            changed (callable): called when value changed
        Returns:
            bytes: hash value
        """
        cls._assert_server_side()
        c = cls.compute_model(data)
        if data.get("forceRun") or cls.is_parallel(c):
            return "HashIsUnused"
        m = data["models"]
        res = hashlib.md5()
        fields = sirepo.sim_data.get_class(data.simulationType)._compute_job_fields(
            data, data.report, c
        )
        # values may be string or PKDict
        fields.sort(key=lambda x: str(x))
        for f in fields:
            # assert isinstance(f, pkconfig.STRING_TYPES), \
            #     'value={} not a string_type'.format(f)
            # TODO(pjm): work-around for now
            if isinstance(f, pkconfig.STRING_TYPES):
                x = f.split(".")
                if cls.is_watchpoint(f) and f != "watchpointReports":
                    i = cls.watchpoint_id(f)
                    value = m.watchpointReports.reports[i].item
                else:
                    value = m[x[0]][x[1]] if len(x) > 1 else m[x[0]]
            else:
                value = f
            res.update(
                pkjson.dump_bytes(
                    value,
                    sort_keys=True,
                    allow_nan=False,
                )
            )
        res.update(
            "".join(
                (
                    str(cls.lib_file_abspath(b, data=data, qcall=qcall).mtime())
                    for b in sorted(cls.lib_file_basenames(data))
                ),
            ).encode()
        )
        return res.hexdigest()

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "beamStatisticsReport",
                "bendingMagnet",
                "histogramReport",
                "initialIntensityReport",
                "plotXYReport",
                "undulator",
                "undulatorBeam",
            ),
        )
        if "magneticField" not in dm.bendingMagnet:
            dm.bendingMagnet.magneticField = (
                1e9
                / scipy.constants.c
                * float(dm.electronBeam.bener)
                / float(dm.bendingMagnet.r_magnet)
            )
        if isinstance(dm.beamline, list):
            dm.beamline = PKDict(
                elements=list(map(lambda i: PKDict(model=i.type, item=i), dm.beamline))
            )
        if not "watchpointReports" in dm:
            dm.watchpointReports = PKDict(reports=[])
        n = []
        for m in dm:
            if cls.is_watchpoint(m) and m != "watchpointReports":
                cls.update_model_defaults(dm[m], "watchpointReport")
                i = cls.watchpoint_id(m)
                dm[m].id = i
                dm.watchpointReports.reports.append(
                    PKDict(model="watchpointReport", item=dm[m])
                )
                n.append(m)
        for i in n:
            del dm[i]
        for m in map(lambda i: i.item, dm.beamline.elements):
            cls.update_model_defaults(m, m.type)
        cls._organize_example(data)

    @classmethod
    def shadow_simulation_files(cls, data):
        m = data.models
        if m.simulation.sourceType == "wiggler" and m.wiggler.b_from in ("1", "2"):
            return [cls.shadow_wiggler_file(m.wiggler.trajFile)]
        return []

    @classmethod
    def shadow_wiggler_file(cls, value):
        return cls.lib_file_name_with_model_field("wiggler", "trajFile", value)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = cls._non_analysis_fields(data, r) + [
            "bendingMagnet",
            "electronBeam",
            "geometricSource",
            "rayFilter",
            "simulation.istar1",
            "simulation.npoint",
            "simulation.sourceType",
            "sourceDivergence",
            "undulator",
            "undulatorBeam",
            "wiggler",
        ]
        if (
            r == "initialIntensityReport"
            and data["models"]["beamline"]
            and data["models"]["beamline"]["elements"]
            and len(data["models"]["beamline"]["elements"]) > 0
        ):
            res.append([data["models"]["beamline"]["elements"][0]["item"]["position"]])
        # TODO(pjm): only include items up to the current watchpoint
        if cls.is_watchpoint(r) or r == "beamStatisticsReport":
            res.append("beamline")
        return res

    @classmethod
    def _lib_file_basenames(cls, data, *args, **kwargs):
        return cls.shadow_simulation_files(data)
