# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(("notes",))

    JSPEC_ELEGANT_TWISS_FILENAME = "twiss_output.filename.sdds"

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "beamEvolutionAnimation",
                "coolingRatesAnimation",
                "electronCoolingRate",
                "forceTableAnimation",
                "intrabeamScatteringRate",
                "particleAnimation",
                "ring",
                "twissReport",
            ),
        )
        if "beam_type" not in dm.ionBeam:
            dm.ionBeam.setdefault(
                "beam_type",
                "bunched" if dm.ionBeam.rms_bunch_length > 0 else "continuous",
            )
        if "particle" not in dm.ionBeam:
            dm.ionBeam.particle = "OTHER"
        if "beam_type" not in dm.electronBeam:
            x = dm.electronBeam
            x.beam_type = "continuous" if x.shape == "dc_uniform" else "bunched"
            x.rh = x.rv = 0.004
        if "time_step" not in dm.simulationSettings:
            dm.simulationSettings.time_step = dm.simulationSettings.time / (
                dm.simulationSettings.step_number or 1
            )
        cls._init_models(dm, ("ionBeam", "electronBeam", "simulationSettings"))
        x = dm.simulationSettings
        if x.model == "model_beam":
            x.model = "particle"
        if "ibs" not in x:
            x.ibs = "1"
            x.e_cool = "1"
        if not x.get("ref_bet_x", None):
            x.ref_bet_x = x.ref_bet_y = 10
            for f in (
                "ref_alf_x",
                "ref_disp_x",
                "ref_disp_dx",
                "ref_alf_y",
                "ref_disp_y",
                "ref_disp_dy",
            ):
                x[f] = 0
        # if model field value is less than min, set to default value
        s = cls.schema()
        for m in dm:
            x = dm[m]
            if m in s.model:
                for f in s.model[m]:
                    d = s.model[m][f]
                    if len(d) > 4 and x[f] < d[4]:
                        x[f] = d[2]
        cls._organize_example(data)

    @classmethod
    def jspec_elegant_twiss_path(cls):
        return "{}/{}".format("animation", cls.JSPEC_ELEGANT_TWISS_FILENAME)

    @classmethod
    def jspec_elegant_dir(cls):
        return simulation_db.simulation_dir("elegant")

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == "rateCalculationReport":
            return [
                "cooler",
                "electronBeam",
                "electronCoolingRate",
                "intrabeamScatteringRate",
                "ionBeam",
                "ring",
            ]
        if r == "twissReport":
            return ["twissReport", "ring"]
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        r = data.models.ring
        s = r["latticeSource"]
        if s == "madx":
            res.append(
                cls.lib_file_name_with_model_field("ring", "lattice", r["lattice"])
            )
        elif s == "elegant":
            res.append(
                cls.lib_file_name_with_model_field(
                    "ring", "elegantTwiss", r["elegantTwiss"]
                )
            )
        return res
