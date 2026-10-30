"""Test cortex_plot.pyplot with the plot code in slab.py.jinja

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_WASTE_PREFIX = "waste_summary_"

_WASTE_SCALED_SUFFIX = "_struct_scaled"


def test_slab_pyplot_attributes():
    """Every plt., ax. and fig. attribute in slab.py.jinja exists on the wrapper

    slab.py.jinja is generated from the cortex repo, and an attribute the
    wrapper lacks only fails when a sim reaches that line.
    """
    from pykern import pkio, pkunit
    import re
    import sirepo.resource

    with pkunit.save_chdir_work():
        p = _pyplot()
    s = pkio.read_text(
        sirepo.resource.file_path("template", "cortex", "slab.py.jinja"),
    )
    pkunit.pkeq(
        [],
        sorted(
            n
            for n in set(re.findall(r"\b(?:ax|fig|plt)\.([A-Za-z_]\w*)", s))
            if not hasattr(p, n)
        ),
    )


def test_waste_plot():
    """slab.py.jinja's waste plot runs through the wrapper and loads as listed

    Runs plot_waste_wdr_per_layer from the rendered slab.py.jinja on made-up
    data, then loads each waste plot listed in template.cortex the way
    _save_summary_to_database does.
    """
    from pykern import pkio, pkjson, pkunit
    import pathlib
    import sirepo.template.cortex

    with pkunit.save_chdir_work():
        g = _slab_globals(
            _pyplot(),
            "CLASS_COLORS",
            "SECONDS_PER_YEAR",
            "WASTE_SUMMARY_METRICS",
            "_add_time_reference_lines",
            "_class_regions",
            "_finalize_legend",
            "_format_log_axes",
            "_plot_waste_summary_one",
            "_safe_csv_label",
            "plot_waste_wdr_per_layer",
        )
        s = [
            k
            for k in sirepo.template.cortex._REPORT_TITLE.slabAnimation
            if k.startswith(_WASTE_PREFIX)
        ]
        g["plot_waste_wdr_per_layer"](
            _waste_data(
                [k for k in s if not k.endswith(_WASTE_SCALED_SUFFIX)],
            ),
            pathlib.Path("."),
        )
        for k in s:
            p = sirepo.template.cortex._plot_from_file(
                pkjson.load_any(
                    pkio.read_text(
                        "{}/{}.png.json".format(
                            (
                                "struct_scaled"
                                if k.endswith(_WASTE_SCALED_SUFFIX)
                                else "raw"
                            ),
                            k,
                        )
                    )
                ),
                1,
                "wcllSlabAnimation",
                k,
            )
            f = sirepo.template.cortex.plotdef_to_sim_frame(p)
            pkunit.pkeq("loglog", f.type)
            pkunit.pkeq("time_dependent", f.meta.section)
            pkunit.pkeq(
                [x[1] for x in g["WASTE_SUMMARY_METRICS"]],
                [x.label for x in f.plots],
            )
            pkunit.pkeq(
                p.points,
                sirepo.template.cortex.plot_from_csv(
                    sirepo.template.cortex.csv_from_plot(p)
                ).points,
            )


def _pyplot():
    """Render cortex_plot.py in the current dir, as a run does, and load it"""
    from pykern import pkio, pkrunpy
    from pykern.pkcollections import PKDict
    from sirepo.template import template_common

    pkio.write_text(
        "cortex_plot.py",
        template_common.render_jinja("cortex", PKDict(), "cortex_plot.py"),
    )
    return pkrunpy.run_path_as_module("cortex_plot.py").pyplot


def _slab_globals(pyplot, *names):
    """Definitions of names from the rendered slab.py.jinja, using pyplot as plt

    A name defined in more than one source file keeps its last definition,
    which is the one in effect when slab.py runs.
    """
    from pykern.pkcollections import PKDict
    from sirepo.template import template_common
    import ast
    import math
    import matplotlib.ticker
    import numpy
    import pandas
    import pathlib
    import typing

    d = PKDict()
    for n in ast.parse(
        template_common.render_jinja(
            "cortex",
            PKDict(
                chainPath="chain.xml",
                dagmcPath=".",
                materialDefinition="t = None",
                material_is_plasma_facing="0",
                mpiCores=1,
                simulationSettings_particlesPerBatch=1000,
                simulationSettings_tallyConvergenceThreshold=0.05,
                slabType="WCLL",
            ),
            "slab.py",
        )
    ).body:
        for k in [n.name] if hasattr(n, "name") else getattr(n, "targets", []):
            k = getattr(k, "id", k)
            if k in names:
                d[k] = n
    rv = PKDict(
        {k: getattr(typing, k) for k in ("Dict", "List", "Optional", "Sequence")},
        Path=pathlib.Path,
        Tuple=typing.Tuple,
        math=math,
        mticker=matplotlib.ticker,
        np=numpy,
        pd=pandas,
        plt=pyplot,
    )
    for k in names:
        exec(compile(ast.Module([d[k]], []), "slab.py", "exec"), rv)
    return rv


def _waste_data(stats):
    """Rows for waste_timeseries' columns, one layer per listed waste stat

    Classes change over cooling time, and Fetter's rating crosses 1.0, so the
    class regions and their labels are drawn. The structure scaled columns are
    the unscaled ones over a structural volume fraction of 0.5.
    """
    import numpy
    import pandas

    return pandas.DataFrame(
        [
            dict(
                layer=s[len(_WASTE_PREFIX) :].replace("_", " "),
                Cooling_time_years=t,
                nrc_class="GTCC" if t < 1e-2 else "Class C" if t < 10 else "Class A",
                wdr_long=1e-3 * t**-0.1,
                wdr_short_a=50 / (1 + t),
                wdr_short_b=5 / (1 + t),
                wdr_short_c=0.5 / (1 + t),
                wdr_fetter=2 / (1 + t**0.5),
                structural_volume_fraction=0.5,
                nrc_class_struct_scaled=(
                    "GTCC" if t < 1e-1 else "Class C" if t < 20 else "Class A"
                ),
                wdr_long_struct_scaled=2e-3 * t**-0.1,
                wdr_short_a_struct_scaled=100 / (1 + t),
                wdr_short_b_struct_scaled=10 / (1 + t),
                wdr_short_c_struct_scaled=1 / (1 + t),
                wdr_fetter_struct_scaled=4 / (1 + t**0.5),
            )
            for s in stats
            for t in numpy.logspace(-7, 4, 40)
        ]
    )
