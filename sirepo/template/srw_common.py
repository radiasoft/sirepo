"""SRW simulation_db/template/sim_data independent routines

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import copy
import re


def process_beam_parameters(ebeam):
    import sirepo.sim_data
    import srwpy.srwlib

    sim_data = sirepo.sim_data.get_class("srw")

    def _convert_ebeam_units(field_name, value, to_si=True):
        """Convert values from the schema to SI units (m, rad) and back.

        Args:
            field_name: name of the field in SCHEMA['model']['electronBeam'].
            value: value of the field.
            to_si: if set to True, convert to SI units, otherwise convert back to the units in the schema.

        Returns:
            value: converted value.
        """

        def _invert_value(value):
            return value**-1 if to_si else value

        s = sim_data.schema()
        if field_name in s["model"]["electronBeam"].keys():
            label, field_type = s["model"]["electronBeam"][field_name]
            if field_type == "Float":
                if re.search(r"\[m(m|rad)\]", label):
                    value *= _invert_value(1e3)
                elif re.search(r"\[\xb5(m|rad)\]", label):  # mu
                    value *= _invert_value(1e6)
                elif re.search(r"\[n(m|rad)\]", label):
                    value *= _invert_value(1e9)
        return value

    # if the beamDefinition is "twiss", compute the moments fields and set on ebeam
    moments_fields = [
        "rmsSizeX",
        "xxprX",
        "rmsDivergX",
        "rmsSizeY",
        "xxprY",
        "rmsDivergY",
    ]
    for k in moments_fields:
        if k not in ebeam:
            ebeam[k] = 0
    if "beamDefinition" not in ebeam:
        ebeam["beamDefinition"] = "t"

    if ebeam["beamDefinition"] == "t":  # Twiss
        model = copy.deepcopy(ebeam)
        # Convert to SI units to perform SRW calculation:
        for k in model:
            model[k] = _convert_ebeam_units(k, ebeam[k])
        beam = srwpy.srwlib.SRWLPartBeam()
        beam.from_Twiss(
            _e=model["energy"],
            _sig_e=model["rmsSpread"],
            _emit_x=model["horizontalEmittance"],
            _beta_x=model["horizontalBeta"],
            _alpha_x=model["horizontalAlpha"],
            _eta_x=model["horizontalDispersion"],
            _eta_x_pr=model["horizontalDispersionDerivative"],
            _emit_y=model["verticalEmittance"],
            _beta_y=model["verticalBeta"],
            _alpha_y=model["verticalAlpha"],
            _eta_y=model["verticalDispersion"],
            _eta_y_pr=model["verticalDispersionDerivative"],
        )
        # copy moments values into the ebeam
        for i, k in enumerate(moments_fields):
            v = (
                beam.arStatMom2[i]
                if k in ["xxprX", "xxprY"]
                else beam.arStatMom2[i] ** 0.5
            )
            ebeam[k] = sim_data.srw_format_float(
                _convert_ebeam_units(k, v, to_si=False)
            )
    return ebeam
