"""test particle_beam

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_dispersion():
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo.template import particle_beam
    import numpy

    d = (-2.57, -0.281, 0.5, 0.05)
    b = PKDict(
        num_particles=200000,
        beta_x=29.528,
        alpha_x=-3.237,
        emittance_x=1e-6,
        beta_y=7.347,
        alpha_y=0.986,
        emittance_y=1e-6,
        dtau=1e-3,
        dpt=1e-3,
    )
    p = particle_beam.populate_uncoupled_beam(iseed=123456789, dispersion=d, **b)
    pt = p[:, 5] - p[:, 5].mean()
    for i, v in enumerate(d):
        u = p[:, i] - p[:, i].mean()
        r = (u * pt).mean() / (pt * pt).mean()
        pkunit.pkok(abs(r - v) <= 0.02 * abs(v), "dispersion {}={} != {}", i, r, v)
    # without dispersion, x and pt are uncorrelated
    p = particle_beam.populate_uncoupled_beam(iseed=1, **b)
    pkunit.pkok(
        abs(numpy.corrcoef(p[:, 0], p[:, 5])[0, 1]) < 0.01,
        "x and pt correlated without dispersion",
    )
