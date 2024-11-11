# -*- coding: utf-8 -*-
"""Wrapper to run canvas from the command line.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template.elegant import ElegantMadxConverter
from sirepo.template.lattice import LatticeUtil
import copy
import scipy.constants
import sirepo.lib
import sirepo.pkcli.elegant
import sirepo.pkcli.impactx
import sirepo.pkcli.madx
import sirepo.sim_data
import sirepo.template
import sirepo.template.canvas
import sirepo.template.elegant_common
import sirepo.template.sdds_util

_SCHEMA = sirepo.sim_data.get_class("canvas").schema()
_ELEGANT_INPUT_FILE = "elegant.ele"
_IMPACTX_RUN_FILE = "run.py"
_MADX = sirepo.sim_data.get_class("madx")
_MADX_INPUT_FILE = "in.madx"
_MODEL_FIELD_MAP = PKDict(
    APERTURE=PKDict(
        _type="COLLIMATOR",
        _fields=["name", "l", "_id"],
    ),
    DRIFT=PKDict(
        _fields=["name", "l", "_id"],
    ),
    MONITOR=PKDict(
        _fields=["name", "_id"],
    ),
    QUADRUPOLE=PKDict(
        _fields=["name", "l", "k1", "k1s", "_id"],
    ),
    RFCAVITY=PKDict(
        _fields=["name", "l", "volt", "freq", "_id"],
    ),
    SBEND=PKDict(
        _fields=[
            "name",
            "l",
            "angle",
            "fint",
            "fintx",
            "e1",
            "e2",
            "_id",
        ],
    ),
    SEXTUPOLE=PKDict(
        _fields=["name", "l", "k2", "k2s", "_id"],
    ),
)


def run(cfg_dir):
    return sirepo.pkcli.impactx.run(cfg_dir)


def run_background(cfg_dir):
    d = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if (
        d.models.distribution.distributionType == "File"
        and not sirepo.template.sdds_util.is_sdds_file(
            d.models.distribution.distributionFile
        )
    ):
        f1 = _MADX.lib_file_name_with_model_field(
            "distribution", "distributionFile", d.models.distribution.distributionFile
        )
    else:
        template_common.exec_parameters()
        f1 = str(pkio.py_path("diags/openPMD/monitor.h5"))
    f2 = sirepo.template.canvas.INPUT_IMPACTX_BEAM_FILE
    pkio.py_path(f1).copy(pkio.py_path(f2))
    _write_madx(d, f2)
    # TODO(pjm): conditional generation
    _write_elegant(f2)
    _write_impactx(f2)
    _run_all()


def _run_all():
    # TODO(pjm): conditional execution
    with pkio.save_chdir("madx"):
        sirepo.pkcli.madx._run_madx()

    with pkio.save_chdir("elegant"):
        pksubprocess.check_call_with_signals(
            ["elegant", _ELEGANT_INPUT_FILE],
            msg=pkdlog,
            output=sirepo.pkcli.elegant.ELEGANT_LOG_FILE,
            env=sirepo.template.elegant_common.subprocess_env(),
        )

    with pkio.save_chdir("impactx"):
        pksubprocess.check_call_with_signals(
            ["python", _IMPACTX_RUN_FILE],
            msg=pkdlog,
            output="impactx.log",
        )


def _write_elegant(input_file):
    elegant = sirepo.sim_data.get_class("elegant")

    def madx_to_elegant(madx_in, source_file):
        d = ElegantMadxConverter(qcall=None).from_madx(
            sirepo.lib.Importer("madx").parse_file(madx_in),
        )
        for idx, cmd in enumerate(d.models.commands):
            if cmd._type == "run_setup":
                cmd.parameters = ""
                cmd.centroid = ""
                cmd.sigma = "run_setup.sigma.sdds"
                cmd.output = "run_setup.output.sdds"
                cmd.use_beamline = d.models.simulation.visualizationBeamlineId
            if cmd._type == "twiss_output":
                cmd.filename = "twiss_output.filename.sdds"
            if cmd._type == "bunched_beam":
                break
        del d.models.commands[idx]
        d.models.commands.insert(
            idx,
            elegant.model_defaults("command_sdds_beam").pkupdate(
                _id=LatticeUtil.max_id(d) + 1,
                _type="sdds_beam",
                input_type="openPMD",
                input=source_file,
                center_transversely=1,
            ),
        )
        for el in d.models.elements:
            if el.type == "CSBEND":
                el.n_slices = 20
            elif el.type == "MONI":
                el.type = "WATCH"
                el.filename = f"{el.name}.filename-%03ld.sdds"
        util = LatticeUtil(d, elegant.schema())
        _add_last_element(
            util,
            PKDict(type="WATCH", name="end", filename=f"end.filename-001.sdds"),
        )
        return d

    s = sirepo.lib.SimData(
        madx_to_elegant(f"madx/{_MADX_INPUT_FILE}", input_file),
        pkio.py_path(_ELEGANT_INPUT_FILE),
        sirepo.template.import_module("elegant").LibAdapter(),
    )
    pkio.unchecked_remove("elegant")
    pkio.mkdir_parent("elegant")
    s.write_files("elegant")
    sirepo.template.elegant.convert_to_sdds(
        str(pkio.py_path("elegant").join(input_file))
    )


def _add_last_element(util, el):
    i = util.max_id + 1
    el._id = i
    util.data.models.elements.append(el)
    util.select_beamline()["items"].append(i)


def _write_impactx(input_file):
    impactx = sirepo.sim_data.get_class("impactx")

    def update_beam(data, input_file):
        data.models.distribution.pkupdate(
            PKDict(
                distributionType="File",
                distributionFile=input_file,
            )
        )
        pkio.py_path(input_file).copy(
            pkio.py_path(
                impactx.lib_file_name_with_model_field(
                    "distribution", "distributionFile", input_file
                )
            )
        )
        # add an "end" monitor
        util = LatticeUtil(data, impactx.schema())
        _add_last_element(
            util,
            PKDict(
                type="BEAMMONITOR",
                name="end",
            ),
        )
        return data

    i = sirepo.template.import_module("impactx").LibAdapter()
    s = sirepo.lib.SimData(
        update_beam(i.parse_file(f"madx/{_MADX_INPUT_FILE}"), input_file),
        pkio.py_path(_IMPACTX_RUN_FILE),
        i,
    )
    pkio.unchecked_remove("impactx")
    pkio.mkdir_parent("impactx")
    s.write_files("impactx")


def _write_madx(data, input_file):
    pkio.py_path(input_file).copy(
        pkio.py_path(
            _MADX.lib_file_name_with_model_field("bunch", "sourceFile", input_file)
        )
    )
    s = sirepo.lib.SimData(
        _to_madx(data, input_file),
        pkio.py_path(_MADX_INPUT_FILE),
        sirepo.template.import_module("madx").LibAdapter(),
    )
    pkio.unchecked_remove("madx")
    pkio.mkdir_parent("madx")
    s.write_files("madx")


def _beam_settings_from_file(input_file, model=None):
    def _read_beam_values(h5):
        return PKDict(
            beam=PKDict(
                gamma=h5.attrs["gamma_ref"],
                mass=h5.attrs["mass_ref"],
                charge=h5.attrs["charge_ref"],
            ),
            twiss=PKDict(
                alfx=h5.attrs["alpha_x"],
                alfy=h5.attrs["alpha_y"],
                betx=h5.attrs["beta_x"],
                bety=h5.attrs["beta_y"],
            ),
        )

    e = sirepo.template.import_module("madx")._read_bunch_file(
        input_file,
        _read_beam_values,
    )
    if model == "twiss":
        return e.twiss
    return PKDict(
        gamma=e.beam.gamma,
        charge=abs(e.beam.charge) / e.beam.charge,
        mass=e.beam.mass
        / scipy.constants.physical_constants["electron volt-kilogram relationship"][0]
        / 1e9,
    )


def _next_id(state):
    res = state.next_id
    state.next_id += 1
    return res


def _to_madx(data, source_file):
    def _command(state, values):
        m = _MADX.model_defaults(f"command_{values._type}")
        m.update(values)
        m._id = _next_id(state)
        return m

    def _val(cv, var_value):
        return cv.eval_var_with_assert(var_value)

    util = LatticeUtil(data, _SCHEMA)
    cv = sirepo.template.canvas.code_var(data.models.rpnVariables)
    state = PKDict(
        next_id=util.max_id + 1,
        util=util,
    )
    bunch = PKDict(
        beamDefinition="file",
        sourceFile=source_file,
    )
    res = PKDict(
        models=PKDict(
            beamlines=copy.deepcopy(data.models.beamlines),
            bunch=bunch,
            commands=[
                _command(
                    state,
                    PKDict(
                        _type="beam",
                        particle=data.models.distribution.species,
                    ).pkupdate(_beam_settings_from_file(source_file)),
                ),
                _command(
                    state,
                    PKDict(
                        _type="twiss",
                        file="1",
                    ).pkupdate(_beam_settings_from_file(source_file, model="twiss")),
                ),
            ]
            + sirepo.template.madx.command_template("particle", _next_id(state)),
            elements=[],
            rpnVariables=data.models.rpnVariables,
            simulation=PKDict(
                computeTwissFromParticles="0",
                visualizationBeamlineId=data.models.simulation.visualizationBeamlineId,
            ),
        ),
    )

    for e in data.models.elements:
        assert e.type in _MODEL_FIELD_MAP, f"Missing type handler: {e.type}"
        if e.type in _MODEL_FIELD_MAP:
            t = _MODEL_FIELD_MAP[e.type].get("_type", e.type)
            m = _MADX.model_defaults(t).pkupdate(type=t)
            for f in _MODEL_FIELD_MAP[e.type]._fields:
                m[f] = e[f]
            res.models.elements.append(m)
            if e.type == "SBEND":
                m.hgap = _val(cv, e.gap) / 2
                _add_dipedges(res, m, state)
            elif e.type == "RFCAVITY":
                m.lag = -(_val(cv, e.phase) + 90) / 360
                m.volt = _val(cv, m.volt) * 1e-6
                m.freq = _val(cv, m.freq) * 1e-6
            elif e.type == "APERTURE":
                m.apertype = "rectangle" if e.shape == "rectangular" else "ellipse"
                m.aperture = f"{{{e.xmax},{e.ymax}}}"
    sirepo.template.madx.add_observers(LatticeUtil(res, _MADX.schema()), "MONITOR")
    return res


def _add_dipedges(data, sbend, state):
    if not sbend.l:
        raise AssertionError(f"SBEND missing length: {sbend.name}")
    d1 = _MADX.model_defaults("DIPEDGE").pkupdate(
        _id=_next_id(state),
        type="DIPEDGE",
        name=f"DP1_{sbend.name}",
        hgap=sbend.hgap,
        fint=sbend.fint,
        h=f"{sbend.angle} / {sbend.l}",
        e1=sbend.e1,
    )
    d2 = _MADX.model_defaults("DIPEDGE").pkupdate(
        _id=_next_id(state),
        type="DIPEDGE",
        name=f"DP2_{sbend.name}",
        hgap=sbend.hgap,
        fint=sbend.fintx,
        h=f"{sbend.angle} / {sbend.l}",
        e1=sbend.e2,
    )
    sbend.hgap = 0
    sbend.fint = 0
    sbend.fintx = -1
    sbend.e1 = 0
    sbend.e2 = 0
    data.models.elements += [d1, d2]
    for bl in data.models.beamlines:
        _add_dipedges_to_beamline(data, bl, sbend, d1, d2, state)


def _add_dipedges_to_beamline(data, beamline, sbend, d1, d2, state):
    bl = []
    for i in beamline["items"]:
        e = state.util.id_map.get(abs(i))
        if e and e.get("type") == "SBEND" and e._id == sbend._id:
            bl.append(d1._id)
            bl.append(i)
            bl.append(d2._id)
            continue
        bl.append(i)
    beamline["items"] = bl
