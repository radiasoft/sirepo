"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
import sirepo.util


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "SPNTRK",
                "SRLOSS",
                "bunch",
                "bunchAnimation",
                "bunchAnimation2",
                "elementStepAnimation",
                "energyAnimation",
                "opticsReport",
                "particle",
                "particleAnimation",
                "particleCoordinate",
                "simulationSettings",
                "tunesReport",
                "twissReport2",
                "twissSummaryReport",
            ),
        )
        if "coordinates" not in dm.bunch:
            b = dm.bunch
            b.coordinates = []
            for _ in range(b.particleCount2):
                c = PKDict()
                cls.update_model_defaults(c, "particleCoordinate")
                b.coordinates.append(c)
        # move spntrk from simulationSettings (older) or bunch if present
        for m in "simulationSettings", "bunch":
            if "spntrk" in dm:
                dm.SPNTRK.KSO = dm[m].spntrk
                del dm[m]["spntrk"]
                for f in "S_X", "S_Y", "S_Z":
                    if f in dm[m]:
                        dm.SPNTRK[f] = dm[m][f]
                        del dm[m][f]
        if dm.elementStepAnimation.x == "Y-DY":
            # fixup bad AGS booster example data
            dm.elementStepAnimation.x = "YDY"
        for e in dm.elements:
            cls.update_model_defaults(e, e.type)
        cls._organize_example(data)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == "tunesReport":
            return [r]
        res = ["particle", "bunch"]
        if compute_model == "bunchReport":
            if data.models.bunch.match_twiss_parameters == "1":
                res.append("simulation.visualizationBeamlineId")
        res += [
            "beamlines",
            "elements",
        ]
        if compute_model == "twissReport":
            res.append("simulation.activeBeamlineId")
        if compute_model == "twissReport2":
            res.append("simulation.visualizationBeamlineId")
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "bunchReport" in analysis_model:
            return "bunchReport"
        if "opticsReport" in analysis_model or analysis_model in (
            "twissReport2",
            "twissSummaryReport",
        ):
            return "twissReport2"
        if "twissReport" == analysis_model:
            return "twissReport"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        bunch = data.models.bunch
        for info in (
            ["OBJET3", "FNAME"],
            ["OBJET3.1", "FNAME2"],
            ["OBJET3.2", "FNAME3"],
        ):
            if bunch.method == info[0] and bunch[info[1]]:
                res.append(
                    cls.lib_file_name_with_model_field("bunch", info[1], bunch[info[1]])
                )
        for el in data.models.elements:
            if el.type == "TOSCA" and el.magnetFile:
                res.append(
                    cls.lib_file_name_with_model_field(
                        "TOSCA", "magnetFile", el.magnetFile
                    )
                )
        return res
