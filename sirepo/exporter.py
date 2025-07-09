"""Export simulations in a single archive

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import sim_data
from sirepo import simulation_db
from sirepo import template
import copy
import sirepo.sim_run
import sirepo.template
import sirepo.util


def create_archive(sim, qcall):
    """Zip up the json file and its dependencies

    Args:
        sim (PKDict): parsed request

    Returns:
        py.path.Local: zip file name
    """
    with sirepo.sim_run.tmp_dir(qcall=qcall) as d:
        return qcall.reply_attachment(
            _create_zip(sim, out_dir=d, qcall=qcall),
            filename=sim.filename,
        )


def _create_zip(sim, out_dir, qcall):
    """Zip up the json file and its dependencies

    Args:
        sim (req): simulation
        out_dir (py.path): where to write to

    Returns:
        py.path.Local: zip file name
    """
    path = out_dir.join(sim.id + ".zip")
    data = simulation_db.open_json_file(sim.type, sid=sim.id, qcall=qcall)
    s = sim_data.get_class(data)
    data = s.sim_run_input_fixup(data)
    data.pkdel("report")
    files = s.lib_files_for_export(data, qcall=qcall)
    files.extend(_run_file(data, sim.template, out_dir, qcall))
    with sirepo.util.write_zip(str(path)) as z:
        for f in files:
            if hasattr(sim.template, "export_filename"):
                n = sim.template.export_filename(
                    sim.filename,
                    f.basename,
                )
            else:
                n = f.basename
            z.write(str(f), n)
        if hasattr(sim.template, "copy_related_sims"):
            for idx, sim_obj in enumerate(data.models.simWorkflow.coupledSims):
                if sim_obj.simulationType and sim_obj.simulationId:
                    d = simulation_db.open_json_file(
                        sim_obj.simulationType, sid=sim_obj.simulationId, qcall=qcall
                    )
                    z.writestr(
                        f"related_sim{idx}.json",
                        pkjson.dump_pretty(d, pretty=True),
                    )
                    for lib_file in sim_data.get_class(
                        sim_obj.simulationType
                    ).lib_file_basenames(d):
                        z.write(
                            sim_data.get_class(sim_obj.simulationType).lib_file_abspath(
                                lib_file, qcall=qcall
                            ),
                            arcname=f"related_sim_{idx}_lib/{lib_file}",
                        )
        z.writestr(
            simulation_db.SIMULATION_DATA_FILE,
            pkjson.dump_pretty(data, pretty=True),
        )
    return path


def _run_file(data, template, out_dir, qcall):
    def _default_path():
        s = template.SCHEMA.constants.simulationSourceExtension
        if s != "py":
            return "{}.{}".format(template.SIM_TYPE, s)
        return "run.py"

    def _files(python_source):
        if isinstance(python_source, PKDict):
            return t
        yield _default_path(), python_source

    for k, v in _files(
        template.python_source_for_model(copy.deepcopy(data), model=None, qcall=qcall)
    ):
        p = out_dir.join(k)
        p.write(v)
        yield p
