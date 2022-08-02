# -*- coding: utf-8 -*-
"""CloudMC execution template.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo import util
from sirepo.template import template_common
import re
import sirepo.sim_data


VOLUME_INFO_FILE = "volumes.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    if report == "dagmcAnimation":
        if not run_dir.join(VOLUME_INFO_FILE).exists():
            raise AssertionError("Volume extraction failed")
        return PKDict(
            percentComplete=100,
            frameCount=1,
            volumes=simulation_db.read_json(VOLUME_INFO_FILE),
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
    )


def get_data_file(run_dir, model, frame, options):
    sim_in = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if model == "dagmcAnimation":
        return PKDict(filename=run_dir.join(f"{frame}.zip"))
    if model == "openmcAnimation":
        return PKDict(filename=run_dir.join(f"{sim_in.models.tally.name}.json"))


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def stateless_compute_read_tallies(data):
    pass


def stateless_compute_validate_material_name(data):
    import openmc

    res = PKDict()
    m = openmc.Material(name="test")
    method = getattr(m, data.component)
    try:
        if data.component == "add_macroscopic":
            method(data.name)
        elif data.component == "add_nuclide":
            method(data.name, 1)
            if not re.search(r"^[^\d]+\d+$", data.name):
                raise ValueError("invalid nuclide name")
        elif data.component == "add_s_alpha_beta":
            method(data.name)
        elif data.component == "add_elements_from_formula":
            method(data.name)
        elif data.component == "add_element":
            method(data.name, 1)
        else:
            raise AssertionError(f"unknown material component: {data.component}")
    except ValueError as e:
        res.error = "invalid material name"
    return res


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    report = data.get("report", "")
    res, v = template_common.generate_parameters_file(data)
    if report == "dagmcAnimation":
        return ""
    v.dagmcFilename = _SIM_DATA.dagmc_filename(data)
    v.tallyName = data.models.tally.name
    v.tallyScore = data.models.tally.score
    v.tallyAspects = data.models.tally.aspects
    v.tallyMeshLowerLeft = util.split_comma_delimited_string(
        data.models.tally.meshLowerLeft, float
    )
    v.tallyMeshUpperRight = util.split_comma_delimited_string(
        data.models.tally.meshUpperRight, float
    )
    v.tallyMeshCellCount = util.split_comma_delimited_string(
        data.models.tally.meshCellCount, int
    )
    return template_common.render_jinja(
        SIM_TYPE,
        v,
    )
