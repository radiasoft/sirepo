"""Test tmap8

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict


def test_comment_math():
    from pykern import pkunit
    from sirepo.template import tmap8

    for c, e in (
        ("m^2/s", r"$\mathrm{m}^{2}/\mathrm{s}$"),
        ("5 K/min", r"5 $\mathrm{K}/\mathrm{min}$"),
        (
            "diffusion activation energy (K) (Eq. 13)",
            r"diffusion activation energy ($\mathrm{K}$) (Eq. 13)",
        ),
        (
            "ramp duration (300 K to 900 K)",
            r"ramp duration (300 $\mathrm{K}$ to 900 $\mathrm{K}$)",
        ),
        ("Boltzmann constant in eV", r"Boltzmann constant in $\mathrm{eV}$"),
        ("s - assuming 10 minutes", r"$\mathrm{s}$ - assuming 10 minutes"),
        ("W/(mum*K)", r"$\mathrm{W}/(\mu\mathrm{m} \cdot \mathrm{K})$"),
        (
            "Units are mumol/mm^3/sqrt(Pa)",
            r"Units are $\mu\mathrm{mol}/\mathrm{mm}^{3}/\sqrt{\mathrm{Pa}}$",
        ),
        ("1/Pa^(1/2)", r"$1/\mathrm{Pa}^{1/2}$"),
        # not units: ordinary words, counts alone, "(-)", "m3"
        ("Boltzmann constant", ""),
        ("1 tritium at", ""),
        ("(-)", ""),
        ("1.0e-29 m3", ""),
        # a "$" would be seen as math by mathRendering
        ("'${units 7.5 mm -> m}'", ""),
        ("$x$ m^2/s", ""),
        (None, ""),
    ):
        pkunit.pkeq(e, tmap8._comment_math(c), "comment={}", c)
    pkunit.pkeq(
        r"$\mathrm{at}/\mathrm{m}^{3}/\mathrm{Pa}^{0.5}$",
        tmap8._unit_math("at/m^3/Pa^0.5"),
    )
    pkunit.pkeq("", tmap8._unit_math("not_a_unit"))


def test_comment_math_client(fc):
    from pykern import pkunit

    v = fc.sr_sim_data(
        "val-2j Tritium Thermal Desorption from Li2TiO3"
    ).models.rpnVariables
    pkunit.pkok(
        any(x.commentMath for x in v), "no commentMath in {}", [x.comment for x in v]
    )
    pkunit.pkok(any(x.unitMath for x in v), "no unitMath")


def test_experimental_file(fc):
    from pykern import pkunit

    d = fc.sr_sim_data("val-2a Ion Implantation Experiment")
    for p in (
        pkunit.data_dir().join("experiment.csv"),
        _xlsx(pkunit.work_dir().join("experiment.xlsx")),
    ):
        pkunit.pkeq(
            None,
            _upload(fc, d, "plotAnimation-experimentalFile", p).get("error"),
        )
    p = pkunit.work_dir().join("one_column.csv")
    p.write("time\n1\n2\n")
    pkunit.pkre(
        "expecting two columns",
        _upload(fc, d, "plotAnimation-experimentalFile", p).error,
    )


def test_expression_units():
    from pykern import pkunit
    from sirepo.template import tmap8

    v = tmap8.code_var(
        [
            PKDict(name="kB", value=1.380649e-23),
            #  inside an expression
            PKDict(name="E", value="${units 0.39 eV -> J} / kB"),
            # TMAP8 substitutes the converted value where D0 is used
            PKDict(name="D0", value=6.9e-7, unit="m^2/s", convertUnit="mum^2/s"),
            PKDict(name="D2", value="D0 * 2"),
            # an expression with a conversion, like ver-1a's diffusivity_SiC
            PKDict(name="F", value="3 * 2", unit="m", convertUnit="mum"),
            PKDict(name="G", value="F + 1"),
        ]
    )
    c = v.compute_cache(PKDict(models=PKDict()), tmap8.SCHEMA)
    # the client looks up an expression's computed value by its text
    pkunit.pkeq(4525.762067404532, c["${units 0.39 eV -> J} / kB"])
    # shown in its own unit, like the value field; used converted by others
    pkunit.pkeq(6.0, c["3 * 2"])
    pkunit.pkeq(6e6, round(c.F, 6))
    pkunit.pkeq(6e6 + 1, round(c["F + 1"], 6))
    pkunit.pkeq(4525.762067404532, c.E)
    pkunit.pkeq(6.9e5, round(c.D0, 6))
    pkunit.pkeq(1.38e6, round(c.D2, 6))
    # a value typed into the table
    pkunit.pkeq(13925.42174586, round(v.eval_var("${units 1.2 eV -> J} / kB")[0], 8))
    # an unknown unit is left unevaluated
    pkunit.pkeq(
        "${units 1 furlong -> m}", tmap8._expand_units("${units 1 furlong -> m}")
    )


def test_import_includes(new_user_fc):
    from pykern import pkunit
    import base64

    fc = new_user_fc
    # as the sim list page does before Import: creates the lib dir and examples
    fc.sr_sim_data("val-2a Ion Implantation Experiment")

    f = PKDict()
    for e in (
        ["params.params", "base.i"],
        ["nested.i"],
        ["history.csv"],
    ):
        r = _import(fc, f)
        pkunit.pkeq("missingFiles", r.get("importState"), "reply={}", r)
        pkunit.pkeq(e, r.missingFiles)
        for n in e:
            f[n] = base64.b64encode(pkunit.data_dir().join(n).read_binary()).decode()
    d = _import(fc, f)
    pkunit.pkeq("main", d.models.simulation.name)
    s = d.models.simulationSettings
    pkunit.pkeq("main.i", s.inputFile)
    pkunit.pkeq(["history.csv"], s.dataFiles)
    pkunit.pkeq(
        ["diffusivity", "temperature", "end_time"],
        [p.name for p in d.models.rpnVariables],
    )
    pkunit.pkeq("diffusivity", d.models.rpnVariables[0].comment)
    t = _source(fc, d)
    pkunit.pkok("!include" not in t, "merged input has !include: {}", t)
    # like elegant, the generated input refers to the lib file
    pkunit.pkre(r"data_file = simulationSettings-dataFile.history.csv\n", t)
    _assert_export_runnable(fc, d)
    # same name, different content: stored under a new name
    f["history.csv"] = base64.b64encode(b"time,temperature\n0,1\n9,2\n").decode()
    d = _import(fc, f)
    pkunit.pkeq(["history-2.csv"], d.models.simulationSettings.dataFiles)
    # the merged input names history-2.csv, so it differs from main.i too
    pkunit.pkeq("main-2.i", d.models.simulationSettings.inputFile)
    pkunit.pkre(
        r"data_file = simulationSettings-dataFile.history-2.csv\n", _source(fc, d)
    )
    # same content as the first import: its files are reused
    f["history.csv"] = base64.b64encode(
        pkunit.data_dir().join("history.csv").read_binary()
    ).decode()
    d = _import(fc, f)
    pkunit.pkeq("main.i", d.models.simulationSettings.inputFile)
    pkunit.pkeq(["history.csv"], d.models.simulationSettings.dataFiles)


def test_log_file():
    from pykern import pkunit
    from sirepo.template import tmap8

    d = pkunit.work_dir().join("log_file")
    if d.exists():
        d.remove()
    d.ensure(dir=True)
    d.join("run.log").write("one core")

    def _log():
        return tmap8.get_data_file(
            d, "animation", tmap8.SCHEMA.constants.logFileFrameId, None
        )

    # TMAP8's output is in the run log on one core, otherwise the MPI log
    pkunit.pkeq("run.log.txt", _log().reply_uri)
    d.join("mpi_run.log").write("mpi")
    pkunit.pkeq("mpi_run.log.txt", _log().reply_uri)


def test_mc_failed_samples():
    from pykern import pkunit
    from sirepo.template import tmap8

    def _samples(*samples):
        d = pkunit.work_dir().join("mc_failed_samples")
        if d.exists():
            d.remove()
        d.ensure(dir=True)
        for i, rows in enumerate(samples):
            d.join(f"main_out_sub{i:02d}_csv.csv").write(
                "time,v\n" + "".join(f"{t},{v}\n" for t, v in rows)
            )
        return d

    # sample 0 failed at the start, sample 2 failed part way
    d = _samples(
        [(0, 0)],
        [(0, 1), (1, 2), (2, 3)],
        [(0, 1), (0.5, 9)],
        [(0, 1), (2, 5)],
    )
    m = tmap8._mc_samples(d)
    pkunit.pkeq(2, m.failed)
    pkunit.pkeq(
        ["main_out_sub01_csv.csv", "main_out_sub03_csv.csv"],
        [x.basename for x in m.converged],
    )
    # on the times of the sample with the most, only converged samples
    a = tmap8._mc_aggregate(m.converged)
    pkunit.pkeq([0, 1, 2], a.time.tolist())
    pkunit.pkeq([1.0, 2.5, 4.0], a.v_mean.tolist())
    pkunit.pkeq(
        "2 of 4 samples did not converge and are not included in the statistics",
        tmap8.post_execution_processing(success_exit=True, run_dir=d),
    )
    d = _samples([(0, 1), (1, 2)], [(0, 1), (1, 3)])
    pkunit.pkeq(None, tmap8.post_execution_processing(success_exit=True, run_dir=d))
    d = _samples([(0, 1)], [(0, 1)])
    with pkunit.pkexcept("None of the 2 samples converged"):
        tmap8.post_execution_processing(success_exit=True, run_dir=d)


def test_parameter_groups():
    from pykern import pkunit
    import pyhit
    from sirepo.template import tmap8

    t = pkunit.data_dir().join("groups.i").read()
    p = tmap8._extract_parameters(pyhit.parse(t), tmap8._parameter_groups(t))
    pkunit.pkeq(
        [
            ("no_heading", ""),
            ("length", "Geometry"),
            ("area", "Geometry"),
            ("trap_density", "Trap 1 parameters"),
            ("ref", "Trap 1 parameters"),
        ],
        [(v.name, v.group) for v in p],
    )


def test_parameter_groups_filled(fc):
    from pykern import pkunit

    d = fc.sr_sim_data("val-2j Tritium Thermal Desorption from Li2TiO3")
    for v in d.models.rpnVariables:
        v.pkdel("group")
    # simulations from prior versions get groups when loaded
    r = fc.sr_post("saveSimulationData", d)
    pkunit.pkeq("Physical Constants", r.models.rpnVariables[0].group)
    pkunit.pkeq(8, len(set(v.group for v in r.models.rpnVariables)))


def test_post_execution_processing():
    from pykern import pkunit
    from sirepo.template import tmap8

    # an excerpt of a failed run's log; *.log files are ignored by git
    # not empty_work_dir(), which holds the fc tests' db
    d = pkunit.work_dir().join("not_converged").ensure(dir=True)
    pkunit.data_dir().join("not_converged.txt").copy(d.join("mpi_run.log"))
    pkunit.pkeq(
        "Solve failed and timestep already at or below dtmin, cannot continue!\n"
        + "The following occurred in the TimeStepper 'ConstantDT' of type ConstantDT.",
        tmap8.post_execution_processing(success_exit=False, run_dir=d),
    )
    pkunit.pkeq(None, tmap8.post_execution_processing(success_exit=True, run_dir=d))
    # no MOOSE error, so job_cmd uses its default
    pkunit.pkeq(
        None,
        tmap8.post_execution_processing(success_exit=False, run_dir=pkunit.data_dir()),
    )


def test_uncertainty_export(fc):
    from pykern import pkunit

    z = _export(
        fc, fc.sr_sim_data("val-2a Ion Implantation Experiment with uncertainty")
    )
    n = set(z.namelist())
    pkunit.pkok({"main.i", "sub.i"} <= n, "missing main.i or sub.i in zip={}", n)
    pkunit.pkok("tmap8.i" not in n, "unexpected tmap8.i in zip={}", n)
    m = z.read("main.i").decode()
    pkunit.pkre(r"input_files = 'sub.i'", m)
    pkunit.pkre(r"param_names = 'diffusivity_D_sampled ", m)
    pkunit.pkre(r"\ndiffusivity_D_sampled = 3e-10\n", z.read("sub.i").decode())


def test_uncertainty_outputs(fc):
    from pykern import pkunit

    t = _source(fc, fc.sr_sim_data("ver-1a Depleting Source Problem with uncertainty"))
    # outputs = '' means all outputs, so it must not become none
    pkunit.pkre(r"\[cumulative_release_right\][^\[]*outputs = ''", t)
    pkunit.pkok("outputs = none" not in t, "unexpected outputs = none")


def test_uncertainty_units(fc):
    from pykern import pkunit

    t = _source(
        fc, fc.sr_sim_data("val-2a Ion Implantation Experiment with uncertainty")
    )
    # the sampler sets a value in the original unit, which is then converted
    pkunit.pkre(
        r"\ndiffusivity_D = '\$\{units \$\{diffusivity_D_sampled\} m\^2/s -> mum\^2/s\}'",
        t,
    )
    pkunit.pkre(r"\ndiffusivity_D_sampled = 3e-10\n", t)


def test_unit_conversion():
    from pykern import pkjson, pkunit
    from sirepo.template import tmap8

    for k, v in pkjson.load_any(
        pkunit.data_dir().join("moose_units.json")
    ).conversions.items():
        a, b = (x.strip() for x in k.split("->"))
        c = tmap8._unit_conversion(a, b)
        pkunit.pkok(c, "unknown conversion={}", k)
        pkunit.pkok(
            abs(c[0] + c[1] - v) <= 1e-5 * abs(v),
            "conversion={} expect={} actual={}",
            k,
            v,
            c[0] + c[1],
        )
    pkunit.pkeq(None, tmap8._unit_conversion("m", "s"))
    # values from tmap8 --show-input
    for a, b, v in (
        ("W/(mum*K)", "W/(m*K)", 1e6),
        ("m^-2", "mum^-2", 1e-12),
        ("1/s", "1/h", 3600),
    ):
        c = tmap8._unit_conversion(a, b)
        pkunit.pkok(c and abs(c[0] - v) <= 1e-9 * v, "{} -> {} {}", a, b, c)
    # MOOSE rejects these ("Expected a number", "Unknown unit 'sqrt'"),
    # though comments use them and they're rendered
    for a, b in (
        ("Pa^0.5", "kPa^0.5"),
        ("mol/sqrt(Pa)", "mol/sqrt(kPa)"),
        ("m^(2)", "mum^(2)"),
    ):
        pkunit.pkeq(None, tmap8._unit_conversion(a, b), "{} -> {}", a, b)
        pkunit.pkok(tmap8._unit_math(a), "not rendered {}", a)


def _assert_export_runnable(fc, data):
    """The exported tmap8.i names data files which are in the zip"""
    from pykern import pkunit
    import re

    z = _export(fc, data)
    n = set(z.namelist())
    f = re.findall(r"data_file = (\S+)", z.read("tmap8.i").decode())
    pkunit.pkok(f, "no data_file in tmap8.i")
    for x in f:
        pkunit.pkok(x in n, "data_file={} not in zip={}", x, n)


def _export(fc, data):
    import io, zipfile

    r = fc.sr_get(
        "exportArchive",
        PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=data.models.simulation.simulationId,
            filename="anything.zip",
        ),
    )
    r.assert_success()
    return zipfile.ZipFile(io.BytesIO(r.data))


def _import(fc, files):
    from pykern import pkjson, pkunit

    return fc.sr_post_form(
        "importFile",
        PKDict(
            folder="/",
            **(
                PKDict(arguments=pkjson.dump_str(PKDict(files=files)))
                if files
                else PKDict()
            ),
        ),
        PKDict(simulation_type=fc.sr_sim_type),
        file=pkunit.data_dir().join("main.i"),
    )


def _source(fc, data):
    from pykern import pkcompat

    return pkcompat.from_bytes(
        fc.sr_get(
            "pythonSource",
            PKDict(
                simulation_type=fc.sr_sim_type,
                simulation_id=data.models.simulation.simulationId,
            ),
        ).data
    )


def _upload(fc, data, file_type, path):
    return fc.sr_post_form(
        "uploadLibFile",
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=data.models.simulation.simulationId,
            file_type=file_type,
        ),
        data=PKDict(),
        file=path,
    )


def _xlsx(path):
    import openpyxl

    w = openpyxl.Workbook()
    w.active.append(["time", "flux"])
    for i in range(3):
        w.active.append([i, i * 2.5])
    w.save(str(path))
    return path
