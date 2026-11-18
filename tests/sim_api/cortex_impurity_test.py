"""test cortex impurity comparison

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

#: times (years after irradiation) of the impurity comparison test data
_YEARS = [1.0 / (365 * 24 * 3600), 1.0 / 365, 1.0, 10.0, 100.0, 1000.0]


def test_reports():
    from pykern import pkjson, pkunit
    from pykern.pkcollections import PKDict
    import sirepo.resource
    import sirepo.sim_api.cortex.batch
    import sirepo.template.cortex

    c = sirepo.template.cortex
    pkunit.pkeq(
        PKDict(blanket="HCPB", impurity=None),
        c.report_parts("hcpbSlabAnimation"),
    )
    pkunit.pkeq(
        PKDict(blanket="WCLL", impurity="max"),
        c.report_parts("wcllSlabMaxImpurityAnimation"),
    )
    pkunit.pkeq(
        PKDict(blanket="HCLL", impurity="min"),
        c.report_parts("hcllSlabMinImpurityAnimation"),
    )
    for r in ("xSlabAnimation", "hcpbSlabNoImpurityAnimation", "hcpbSlabAnimationx"):
        with pkunit.pkexcept("invalid report"):
            c.report_parts(r)
    # every report is a slab and has its schema entries
    s = pkjson.load_any(sirepo.resource.static("json", "cortex-schema.json"))
    for r in c.SIM_VERSION:
        pkunit.pkeq("slabAnimation", c._report_type(r))
        for k in ("frameIdFields", "model", "view"):
            pkunit.pkok(r in s[k], "report={} not in schema {}", r, k)
    pkunit.pkeq(
        [r for r in c.SIM_VERSION if c.report_parts(r).impurity is None],
        list(c.NEUTRONICS_REPORTS),
    )
    # batch only runs the neutronics reports
    pkunit.pkeq(
        sorted(c.NEUTRONICS_REPORTS),
        sirepo.sim_api.cortex.batch._reports(PKDict()),
    )
    with pkunit.pkexcept("invalid report"):
        sirepo.sim_api.cortex.batch._reports(
            PKDict(reports=["hcpbSlabMinImpurityAnimation"]),
        )


def test_impurity_components():
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.template.cortex

    def _c(name, percent, min_percent=None, max_percent=None):
        return PKDict(
            component_type="element",
            component=name,
            percent=percent,
            min_percent=min_percent,
            max_percent=max_percent,
        )

    def _percent(components):
        return PKDict((c.component, round(c.percent, 10)) for c in components)

    f = sirepo.template.cortex._impurity_components
    # Stainless Steel 316: Fe is the balance; Cr, Ni and Mo have ranges with a
    # min > 0, so they aren't impurities; Mn, Si, P, C and S are
    s = [
        _c("fe", 65.65),
        _c("cr", 17.5, 16.5, 18.5),
        _c("ni", 11.5, 10.0, 13.0),
        _c("mo", 2.25, 2.0, 2.5),
        _c("mn", 2.0, 0.0, 2.0),
        _c("si", 1.0, 0.0, 1.0),
        _c("p", 0.05, 0.0, 0.05),
        _c("c", 0.03, 0.0, 0.03),
        _c("s", 0.02, 0.0, 0.02),
    ]
    pkunit.pkeq(_percent(s), _percent(f(s, None)))
    # no Targets were given, so the defaults are the max
    pkunit.pkeq(_percent(s), _percent(f(s, "max")))
    m = f(s, "min")
    pkunit.pkeq(
        PKDict(
            fe=68.75, cr=17.5, ni=11.5, mo=2.25, mn=0.0, si=0.0, p=0.0, c=0.0, s=0.0
        ),
        _percent(m),
    )
    pkunit.pkeq(100.0, round(sum(c.percent for c in m), 10))
    # copies, the sim's components don't change
    pkunit.pkeq(65.65, s[0].percent)
    # an explicit Target below the max
    s[4].percent = 0.5
    s[0].percent += 1.5
    pkunit.pkeq(65.65, round(f(s, "max")[0].percent, 10))
    pkunit.pkeq(2.0, f(s, "max")[4].percent)
    pkunit.pkeq(68.75, round(f(s, "min")[0].percent, 10))
    # the balance is the largest component which isn't an impurity
    pkunit.pkeq(
        PKDict(w=100.0, re=0.0),
        _percent(f([_c("re", 60.0, 0.0, 70.0), _c("w", 40.0)], "min")),
    )
    with pkunit.pkexcept("would be negative"):
        f([_c("w", 0.5), _c("ta", 0.5), _c("re", 99.0, 0.0, 100.0)], "max")
    with pkunit.pkexcept("only impurities"):
        f([_c("re", 100.0, 0.0, 100.0)], "min")


def test_material_definition(monkeypatch):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.sim_run
    import sirepo.template.cortex

    # needs a logged in user, not used by the components
    monkeypatch.setattr(sirepo.sim_run, "cache_dir", lambda *args: "cache")

    d = PKDict(
        report="hcpbSlabMinImpurityAnimation",
        models=PKDict(
            material=PKDict(
                density=7.9,
                percent_type="wo",
                components=[
                    PKDict(
                        component_type="element",
                        component="fe",
                        percent=99.0,
                        min_percent=None,
                        max_percent=None,
                    ),
                    PKDict(
                        component_type="element",
                        component="c",
                        percent=1.0,
                        min_percent=0.0,
                        max_percent=1.0,
                    ),
                ],
            ),
        ),
    )
    t = sirepo.template.cortex._generate_material_definition(d)
    pkunit.pkre(r'element="fe",\s+percent=1\.0,', t)
    pkunit.pkre(r'element="c",\s+percent=0\.0,', t)
    d.report = "hcpbSlabAnimation"
    pkunit.pkre(
        r'element="fe",\s+percent=0\.99,',
        sirepo.template.cortex._generate_material_definition(d),
    )


def test_impurity_comparison():
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.template.cortex

    c = sirepo.template.cortex
    y = c._SECONDS_PER_YEAR
    r = c.stateless_compute_impurity_comparison(
        PKDict(args=impurity_inputs("First_Wall")),
    )
    pkunit.pkeq("First Wall", r.layer)
    pkunit.pkeq(
        ["waste", "waste_struct_scaled", "shutdown_dose", "decay_heat"],
        [x.name for x in r.plots],
    )
    for x in r.plots:
        pkunit.pkeq(b"\x89PNG", bytes(x.png[:4]))
    # the structure scaled classes are the same, so only the plot
    pkunit.pkeq(["waste"], sorted(r.classes))
    x = r.classes.waste
    pkunit.pkeq(
        [86_400, y, 10 * y, 100 * y, 1000 * y],
        [round(k.coolingSeconds) for k in x],
    )
    pkunit.pkeq(
        ["Class B", "Class B", "Class B", "Class A", "Class A"],
        [k.max.nrcClass for k in x],
    )
    pkunit.pkeq(["Class A"] * 5, [k.min.nrcClass for k in x])
    pkunit.pkeq([False] * 5, [k.max.fetterExceeds for k in x])
    # different structure scaled classes are kept
    a = impurity_inputs("First_Wall")
    a.max.waste_struct_scaled = waste_summary_csv(_YEARS, [5.0] * 6, [0.5] * 6)
    pkunit.pkeq(
        ["GTCC"] * 5,
        [
            k.max.nrcClass
            for k in c.stateless_compute_impurity_comparison(
                PKDict(args=a),
            ).classes.waste_struct_scaled
        ],
    )
    # Armor has no structure scaled ratings
    pkunit.pkeq(
        ["waste", "shutdown_dose", "decay_heat"],
        [
            x.name
            for x in c.stateless_compute_impurity_comparison(
                PKDict(args=impurity_inputs("Armor")),
            ).plots
        ],
    )
    a = impurity_inputs("Armor")
    a.min.waste = waste_summary_csv(_YEARS[1:], [0.05] * 5, [0.5] * 5)
    with pkunit.pkexcept("different times"):
        c.stateless_compute_impurity_comparison(PKDict(args=a))
    a = impurity_inputs("Armor")
    a.min.pkdel("decay_heat")
    with pkunit.pkexcept("different files"):
        c.stateless_compute_impurity_comparison(PKDict(args=a))
    with pkunit.pkexcept("invalid report"):
        c.impurity_report("hcpbSlabMinImpurityAnimation", "max")
    pkunit.pkeq(
        "hcllSlabMinImpurityAnimation",
        c.impurity_report("hcllSlabAnimation", "min"),
    )


def test_nrc_class():
    """The port matches slab.py.jinja _classify_from_ratios"""
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    import itertools
    import numpy
    import re
    import sirepo.resource
    import sirepo.template.cortex
    import typing

    c = sirepo.template.cortex
    t = pkio.read_text(
        sirepo.resource.file_path("template", "cortex", "slab.py.jinja"),
    )
    g = PKDict(Tuple=typing.Tuple)
    exec(
        re.search(r"^def _classify_from_ratios.*?(?=^def )", t, re.M | re.S).group(0),
        g,
    )
    v = (0.0, 0.05, 0.5, 5.0)
    n = 0
    for t1, a, b, x in itertools.product(v, v, v, v):
        r = PKDict(
            {
                c._NRC_TABLE1: numpy.array([t1]),
                c._NRC_TABLE2[0]: numpy.array([a]),
                c._NRC_TABLE2[1]: numpy.array([b]),
                c._NRC_TABLE2[2]: numpy.array([x]),
            }
        )
        pkunit.pkeq(
            g._classify_from_ratios(t1, (a, b, x)),
            c._nrc_class(r, 0),
            "ratios={}",
            (t1, a, b, x),
        )
        n += 1
    pkunit.pkeq(4**4, n)


def impurity_inputs(layer):
    """stateless_compute_impurity_comparison args for layer

    Waste: max impurities Class B until 100 years, then Class A; no impurities
    Class A. Decay heat and shutdown dose: max impurities 10% higher.
    """
    from pykern.pkcollections import PKDict
    import sirepo.template.cortex

    c = sirepo.template.cortex
    rv = PKDict(layer=layer)
    for i, a, v in (
        ("max", [5.0] * 4 + [0.5] * 2, 1.1),
        ("min", [0.5] * 6, 1.0),
    ):
        rv[i] = PKDict()
        for k in c.impurity_comparison_files(layer):
            if k.startswith("waste"):
                rv[i][k] = waste_summary_csv(_YEARS, [0.05] * 6, a)
            else:
                rv[i][k] = "Time,Other," + c._IMPURITY_LAYERS[layer][k] + "\n"
                for y in _YEARS:
                    rv[i][k] += f"{y},1.0,{v / (1 + y)}\n"
    return rv


def waste_summary_csv(years, table1, table2_class_a):
    """A waste summary csv like slab.py.jinja's

    Table 2 Class B and C are a tenth and a hundredth of Class A, Fetter is
    half of Table 1.
    """
    import sirepo.template.cortex

    c = sirepo.template.cortex
    rv = ",".join(
        ["Time after irradiation [years]", c._NRC_TABLE1, *c._NRC_TABLE2, c._FETTER]
    )
    for y, t1, a in zip(years, table1, table2_class_a):
        rv += "\n" + ",".join(str(x) for x in (y, t1, a, a / 10, a / 100, t1 / 2))
    return rv + "\n"
