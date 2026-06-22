# -*- coding: utf-8 -*-
"""Wrapper to run OPAL from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import pykern.pkcli
import re
import sirepo.mpi
import sirepo.quest
import sirepo.template.lattice
import sirepo.template.opal as template


def run(cfg_dir):
    run_opal()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if "bunchReport" in data.report or data.report == "twissReport":
        template.save_sequential_report_data(data, py.path.local(cfg_dir))


def run_background(cfg_dir):
    run_opal(with_mpi=True, compute_positions=True)


def run_opal(with_mpi=False, compute_positions=False):
    if pkio.py_path(template.TRACK_FIELDMAP_CONVERSION_FILE).exists():
        template_common.exec_parameters(template.TRACK_FIELDMAP_CONVERSION_FILE)
    if with_mpi:
        if (
            sirepo.mpi.cfg().cores < 2
            or simulation_db.read_json(
                template_common.INPUT_BASE_NAME
            ).models.simulation.simulationMode
            == "serial"
        ):
            with_mpi = False
    if with_mpi:
        sirepo.mpi.run_program(
            ["opal", template.OPAL_INPUT_FILE],
            output=template.OPAL_OUTPUT_FILE,
        )
    else:
        pksubprocess.check_call_with_signals(
            ["opal", template.OPAL_INPUT_FILE],
            output=template.OPAL_OUTPUT_FILE,
            msg=pkdlog,
        )
    if compute_positions:
        template_common.exec_parameters(template.OPAL_POSITION_FILE)


def save_autophase_values(sim_id):
    def _parse_phi(sim_dir):
        r = PKDict()
        p = sim_dir.join("animation", template.OPAL_OUTPUT_FILE)
        if not p.exists():
            raise pykern.pkcli.CommandError("simulation must be run first")
        for z in p.read().splitlines():
            m = re.search(r"Saved phases.*?(\w+)#0 .*?([\d.]+)$", z)
            if m:
                r[m.group(1)] = float(m.group(2))
        return r

    def _update_elements(data, phi_by_name):
        c = 0
        for e in data.models.elements:
            if e.name in phi_by_name and "lag" in e:
                e.lag = phi_by_name[e.name]
                c += 1
        if not c:
            raise pykern.pkcli.CommandError("no lag values found to update")

    def _update_option(data):
        o = sirepo.template.lattice.LatticeUtil.find_first_command(data, "option")
        if o is None:
            raise AssertionError("no option command found in simulation")
        o.autophase = 0

    p = pkio.py_path(simulation_db.find_global_simulation("opal", sim_id, checked=True))
    d = simulation_db.open_json_file(
        "opal", path=p.join(simulation_db.SIMULATION_DATA_FILE)
    )
    _update_elements(d, _parse_phi(p))
    _update_option(d)
    with sirepo.quest.start(in_pkcli=True) as qcall:
        with qcall.auth.logged_in_user_set(simulation_db.uid_from_dir_name(p)):
            simulation_db.save_simulation_json(
                d, fixup=False, do_validate=False, qcall=qcall
            )
