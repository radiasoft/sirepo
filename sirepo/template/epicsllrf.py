# -*- coding: utf-8 -*-
"""epicsllrf execution template.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import numpy
import os
import re
import sirepo.sim_data
import subprocess

_STATUS_FILE = "status.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


# run this for the epics server:
# llrfsim --epics llrfsim/examples/two_cav/two_cav.yml


class EpicsDisconnectError(Exception):
    pass


def analysis_job_read_epics_values(data, run_dir, **kwargs):
    p = run_dir.join("prev-status.json")
    e = run_dir.join(_STATUS_FILE)
    if not data.args.get("noCache") and pkio.compare_files(e, p):
        return PKDict()
    e.copy(p, stat=True)
    return PKDict(
        epicsData=_read_epics_data(run_dir, data.args.get("computedValues")),
    )


def background_percent_complete(report, run_dir, is_running):
    return PKDict(
        percentComplete=100,
        frameCount=0,
        alert=_parse_epics_log(run_dir),
        hasEpicsData=run_dir.join(_STATUS_FILE).exists(),
    )


def epics_field_name(epics_prefix, model_name, field):
    return (
        epics_prefix
        + model_name.replace(epics_prefix, "").replace("_", ":")
        + ":"
        + field
    )


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def run_epics_cmd(cmd, server_address):
    env = os.environ.copy()

    # the EPICS_PVA_ADDR_LIST can contain a hostname only,
    # in which case it will use port 5076 for the udp broadcast address.
    # Otherwise the host:port should specificy the udp broadcast address
    # (configured by EPICS_PVA_BROADCAST_PORT on epics server).

    env["EPICS_PVA_AUTO_ADDR_LIST"] = "NO"
    env["EPICS_PVA_ADDR_LIST"] = server_address
    # TODO (gurhar1133): validate cmd
    return subprocess.Popen(
        cmd,
        env=env,
        shell=True,
        stdin=subprocess.PIPE,
    ).wait()


def stateless_compute_get_epics_config(data, **kwargs):
    return PKDict(
        simSchema=simulation_db.read_json(
            _SIM_DATA.lib_file_abspath(
                _SIM_DATA.lib_file_name_with_model_field(
                    "epicsConfig",
                    "epicsSchema",
                    data.args.epicsSchema,
                ),
            ),
        ),
    )


def stateless_compute_update_epics_value(data, **kwargs):
    for f in data.args.fields:
        if (
            run_epics_cmd(
                f"pvput {epics_field_name(data.args.epicsModelPrefix, data.args.model, f.field)} {f.value}",
                data.args.serverAddress,
            )
            != 0
        ):
            return PKDict(
                success=False,
                error=f"Unable to connect to EPICS server: {data.args.serverAddress}",
            )
    return PKDict(success=True)


def stateless_compute_update_signal_generator(data, **kwargs):
    # could have different implementations based on the modelName
    if data.args.modelName == "ZCUSignalGenerator":
        return _set_zcu_signal(data.args.serverAddress, data.args.model)
    raise AssertionError("unknown signal generator modelName: {}", data.args.modelName)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _calculate_computed_values(d, computed_values):
    for f in computed_values:
        fd = computed_values[f]
        if fd.method == "magnitude":
            d[f] = numpy.abs(
                numpy.array(d[fd.args[0]]) + 1j * numpy.array(d[fd.args[1]]),
            ).tolist()
        elif fd.method == "phase":
            d[f] = numpy.angle(
                numpy.array(d[fd.args[0]]) + 1j * numpy.array(d[fd.args[1]]),
                deg=True,
            ).tolist()
        else:
            raise AssertionError(f"unknown computedValue method: {fd.method}")
    return d


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    v.statusFile = _STATUS_FILE
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )


def _read_epics_data(run_dir, computed_values):
    s = run_dir.join(_STATUS_FILE)
    if s.exists():
        d = simulation_db.json_load(s)
        for f in d:
            v = d[f][0]
            if re.search(r"[A-Za-z]{2}", v):
                v = re.sub(r"\(\d+\)", "", v)
            elif v[0] == "[":
                v = re.sub(r"\[|\]", "", v)
                v = [float(x) for x in v.split(",")]
            else:
                v = float(v)
            d[f] = v
        if computed_values:
            _calculate_computed_values(d, computed_values)
        return d
    return PKDict()


def _parse_epics_log(run_dir, log_filename="run.log"):
    return template_common.LogParser(
        run_dir,
        log_filename=log_filename,
        error_patterns=(r"sirepo.template.epicsllrf.EpicsDisconnectError:\s+(.+)",),
        default_msg="",
    ).parse_for_errors()


def _set_zcu_signal(server_address, model):
    # 'model': {'amp': 32000, 'duration': 1023, 'start': 0},
    # 'serverAddress': 'localhost'

    def write_nco_freq(adc=796.8, dac=186.24):
        for v in ([0, 0], [0, 1], [1, 0], [1, 1]):
            run_epics_cmd(
                f"pvput rfsoc_ioc:Root:XilinxRFSoC:RfDataConverter:adcTile[{v[0]}]:adcBlock[{v[1]}]:ncoFrequency {adc}",
                server_address,
            )
        run_epics_cmd(
            f"pvput rfsoc_ioc:Root:XilinxRFSoC:RfDataConverter:dacTile[0]:dacBlock[0]:ncoFrequency {dac}",
            server_address,
        )

    def set_signal(pulse_width=200, pulse_amp=32000, pulse_delay=200):
        # p4p is required to set the Dac values, pvput doesn't work with union array types
        from p4p.client.thread import Context

        ctx = Context(
            "pva",
            dict(
                EPICS_PVA_ADDR_LIST=server_address,
                EPICS_PVA_AUTO_ADDR_LIST="NO",
            ),
        )
        I = numpy.zeros(shape=4096, dtype=numpy.int32, order="C")
        I[pulse_delay : (pulse_delay + pulse_width)] = pulse_amp
        ctx.put("rfsoc_ioc:Root:XilinxRFSoC:Application:DacSigGen:DacI", I)
        Q = numpy.zeros(shape=4096, dtype=numpy.int32, order="C")
        Q[pulse_delay : (pulse_delay + pulse_width)] = pulse_amp
        ctx.put("rfsoc_ioc:Root:XilinxRFSoC:Application:DacSigGen:DacQ", Q)

    write_nco_freq()
    set_signal(model.duration, model.amp, model.start)

    return PKDict(success=True)
