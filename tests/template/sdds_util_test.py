# -*- coding: utf-8 -*-
"""Test for :mod:`sirepo.template.sdds_util`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_sdds_lineplot():
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkjson
    from pykern.pkunit import pkeq
    from sirepo.template.sdds_util import SDDSUtil

    def _format_plot(plot, sdds_units):
        return plot.col_name

    # reduced original elegant output file size using sddsprocess:
    #   sddsprocess B1.output_file.sdds -delete=columns,GammaDeriv,DeltaGammaT1,DeltaGammaT2 -delete=parameters,* -sparse=10 csrcsbend.sdds
    files = ("csrcsbend.sdds",)

    with pkunit.save_chdir_work() as d:
        for f in files:
            actual = SDDSUtil(str(pkunit.data_dir().join(f))).lineplot(
                PKDict(
                    model=PKDict(
                        x="s",
                        y1="LinearDensity",
                        y2="LinearDensityDeriv",
                        y3="DeltaGamma",
                        plotName=f,
                    ),
                    format_plot=_format_plot,
                )
            )
            out = f"{f}.json"
            pkjson.dump_pretty(actual, out)
            expect = pkjson.load_any(pkunit.data_dir().join(out))
            pkeq(expect, actual)
