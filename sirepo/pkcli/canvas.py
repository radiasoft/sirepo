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
import pmd_beamphysics.readers
import scipy.constants
import sirepo.lib
import sirepo.pkcli.elegant
import sirepo.pkcli.madx
import sirepo.sim_data
import sirepo.template
import sirepo.template.canvas
import sirepo.template.elegant_common

_MADX = sirepo.sim_data.get_class("madx")
_MODEL_FIELD_MAP = PKDict(
    DRIFT=PKDict(
        _fields=["name", "type", "l", "_id"],
    ),
    QUADRUPOLE=PKDict(
        _fields=["name", "type", "l", "k1", "k1s", "_id"],
    ),
)


def run(cfg_dir):
    template_common.exec_parameters()
    sirepo.template.canvas.save_sequential_report_data(
        pkio.py_path(cfg_dir),
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
    )


def run_background(cfg_dir):
    d = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if d.models.distribution.distributionType == "File":
        f1 = _MADX.lib_file_name_with_model_field(
            "distribution", "distributionFile", d.models.distribution.distributionFile
        )
    else:
        template_common.exec_parameters()
        f1 = str(pkio.py_path("diags/openPMD/monitor.h5"))
    f2 = "beam.h5"
    pkio.py_path(f1).copy(pkio.py_path(f2))
    _write_madx(pkio.py_path(cfg_dir), d, f2)
    # TODO(pjm): conditional generation
    _write_elegant(pkio.py_path(cfg_dir), d, f2)
    _write_impactx(pkio.py_path(cfg_dir), d, f2)
    _run_all()


def _run_all():
    # TODO(pjm): conditional execution
    with pkio.save_chdir("madx"):
        sirepo.pkcli.madx._run_madx()

    with pkio.save_chdir("elegant"):
        pksubprocess.check_call_with_signals(
            ["elegant", "elegant.ele"],
            msg=pkdlog,
            output=sirepo.pkcli.elegant.ELEGANT_LOG_FILE,
            env=sirepo.template.elegant_common.subprocess_env(),
        )

    with pkio.save_chdir("impactx"):
        pksubprocess.check_call_with_signals(
            ["python", "run.py"],
            msg=pkdlog,
            output="impactx.log",
        )


def _write_elegant(run_dir, data, input_file):
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
            if cmd._type == "twiss_output":
                cmd.filename = "twiss_output.filename.sdds"
            if cmd._type == "bunched_beam":
                break
        del d.models.commands[idx]
        d.models.commands.insert(
            idx,
            elegant.model_defaults("command_sdds_beam").pkupdate(
                _id=LatticeUtil(d, elegant.schema()).max_id + 1,
                _type="sdds_beam",
                input_type="openPMD",
                input=source_file,
                center_transversely=1,
            ),
        )
        return d

    # pkio.py_path('bunch-sourceFile.electron.h5').copy(pkio.py_path(f));

    s = sirepo.lib.SimData(
        madx_to_elegant("madx/in.madx", input_file),
        pkio.py_path("elegant.ele"),
        sirepo.template.import_module("elegant").LibAdapter(),
    )
    pkio.unchecked_remove("elegant")
    pkio.mkdir_parent("elegant")
    s.write_files("elegant")
    sirepo.template.elegant.convert_to_sdds(
        str(pkio.py_path("elegant").join(input_file))
    )


def _write_impactx(run_dir, data, input_file):
    pkio.unchecked_remove("impactx")
    pkio.mkdir_parent("impactx")
    f = sirepo.sim_data.get_class("canvas").lib_file_name_without_type(input_file)
    beamline = LatticeUtil(data, _MADX.schema()).select_beamline().name
    pkio.py_path(input_file).copy(pkio.py_path("impactx").join(f))

    pkio.write_text(
        "impactx/run.py",
        f"""
#!/usr/bin/env python
from impactx import ImpactX, distribution, elements
from rsbeams.rsstats import kinematic
import amrex.space3d
import h5py
import impactx
import pmd_beamphysics.readers
import re
import scipy.constants

sim = ImpactX()

sim.particle_shape = 2  # B-spline order
sim.space_charge = False
sim.init_grids()


def _vector(value, name):
    res = amrex.space3d.PODVector_real_std()
    for v in value[name]:
        res.push_back(v)
    return res


with h5py.File("{ f }", "r") as f:
    pp = pmd_beamphysics.readers.particle_paths(f)
    d = f[pp[-1]]
    if "beam" in d:
        d = d["beam"]

    speciesMass_MeV = (
        d.attrs["mass_ref"]
        / scipy.constants.physical_constants["electron volt-kilogram relationship"][0]
        * 1e-6
    )
    speciesCharge = d.attrs["charge_ref"] / abs(d.attrs["charge_ref"])
    # docs say charge over mass [1/eV], but seems to be [C / kg]
    qm = d.attrs["charge_ref"] / d.attrs["mass_ref"]
    npart = len(d["position/x"])
    kin_energy_MeV = kinematic.Converter(
        mass=d.attrs["mass_ref"],
        mass_unit="SI",
        gamma=d.attrs["gamma_ref"],
    )(silent=True)['kenergy'] * 1e-6
    sim.particle_container().ref_particle().set_charge_qe(speciesCharge).set_mass_MeV(
        speciesMass_MeV
    ).set_kin_energy_MeV(kin_energy_MeV)
    sim.particle_container().add_n_particles(
        _vector(d, "position/x"),
        _vector(d, "position/y"),
        _vector(d, "position/t"),
        _vector(d, "momentum/x"),
        _vector(d, "momentum/y"),
        _vector(d, "momentum/t"),
        qm,
        abs(d.attrs["charge_C"]),
    )

sim.lattice.load_file('../madx/in.madx', nslice=1, beamline='{ beamline }')
sim.periods = 1
sim.evolve()

sim.particle_container().to_df(local=True).to_hdf('final_distribution.h5', 'final')
sim.finalize()
    """,
    )


def _write_madx(run_dir, data, input_file):
    pkio.py_path(input_file).copy(
        pkio.py_path(
            _MADX.lib_file_name_with_model_field("bunch", "sourceFile", input_file)
        )
    )
    s = sirepo.lib.SimData(
        _to_madx(data, input_file),
        pkio.py_path("in.madx"),
        sirepo.template.import_module("madx").LibAdapter(),
    )
    pkio.unchecked_remove("madx")
    pkio.mkdir_parent("madx")
    s.write_files("madx")


def _beam_settings_from_file(input_file):
    def _read_energy(h5):
        return PKDict(
            gamma=h5.attrs["gamma_ref"],
            mass=h5.attrs["mass_ref"],
            charge=h5.attrs["charge_ref"],
        )

    e = sirepo.template.import_module("madx")._read_bunch_file(
        input_file,
        _read_energy,
    )
    return PKDict(
        gamma=e.gamma,
        charge=abs(e.charge) / e.charge,
        mass=e.mass
        / scipy.constants.physical_constants["electron volt-kilogram relationship"][0]
        / 1e9,
    )


def _to_madx(data, source_file):
    def _command(state, values):
        m = _MADX.model_defaults(f"command_{values._type}")
        m.update(values)
        m._id = _next_id(state)
        return m

    def _next_id(state):
        res = state.next_id
        state.next_id += 1
        return res

    state = PKDict(
        next_id=LatticeUtil(data, _MADX.schema()).max_id + 1,
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
                        _type="option",
                        echo="0",
                        info="0",
                        twiss_print="0",
                    ),
                ),
                _command(
                    state,
                    PKDict(
                        _type="beam",
                    ).pkupdate(_beam_settings_from_file(source_file)),
                ),
                _command(
                    state,
                    PKDict(
                        _type="twiss",
                        file="1",
                    ),
                ),
                _command(
                    state,
                    PKDict(
                        _type="ptc_create_universe",
                    ),
                ),
                _command(
                    state,
                    PKDict(
                        _type="ptc_create_layout",
                        method=4,
                        nst=25,
                    ),
                ),
                _command(
                    state,
                    PKDict(
                        _type="ptc_track",
                        element_by_element="1",
                        file="1",
                        icase="6",
                    ),
                ),
                _command(
                    state,
                    PKDict(
                        _type="ptc_track_end",
                    ),
                ),
                _command(
                    state,
                    PKDict(
                        _type="ptc_end",
                    ),
                ),
            ],
            elements=[],
            rpnVariables=PKDict(),
            simulation=PKDict(
                computeTwissFromParticles="0",
                visualizationBeamlineId=data.models.simulation.visualizationBeamlineId,
            ),
        ),
    )

    for e in data.models.elements:
        if e.type in _MODEL_FIELD_MAP:
            m = _MADX.model_defaults(e.type)
            for f in _MODEL_FIELD_MAP[e.type]._fields:
                m[f] = e[f]
            res.models.elements.append(m)

    return res
