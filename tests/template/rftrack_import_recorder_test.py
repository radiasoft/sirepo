"""PyTest for :mod:`sirepo.template.rftrack_import_recorder`

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_autophase_is_a_noop():
    """Unlike track() (see test_track_is_skipped()), autophase()/
    btrack() must not raise at all -- a real generated script's main()
    calls autophase() *before* apply_space_charge(), and raising here
    the same way track() does would abort the script before that (and
    everything else between autophase() and track()) ever runs,
    silently losing it.
    """
    import RF_Track
    import numpy
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    v = RF_Track.Volume()
    d = RF_Track.Drift(1.5)
    d.set_name("D1")
    d.set_aperture(0.02, 0.02, "circular")
    v.add(d, 0, 0, 0, 0, 0, 0)
    v.set_s0(0)
    v.set_s1(1.5)
    p0 = RF_Track.Bunch6dT(
        numpy.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.511, -1.0, 1.0, 0.0]])
    )
    v.unset_t0()
    pkeq(None, v.autophase(p0))
    after = RF_Track.Drift(2.0)
    after.set_name("D2")
    _assert_one(r.calls(), "Volume.autophase", obj=None, args=(p0,))
    _assert_kinds_in_order(
        r.calls(),
        [
            "Drift",
            "Volume.add",
            "Volume.set_s0",
            "Volume.set_s1",
            "Bunch6dT",
            "Volume.autophase",
            "Drift",
        ],
    )


def test_bunch():
    import RF_Track
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    g = RF_Track.Bunch6dT_Generator()
    g.species = "electron"
    p0 = RF_Track.Bunch6dT(g, 100)
    c = r.calls()
    _assert_one(c, "Bunch6dT_Generator", obj=g)
    _assert_one(c, "Bunch6dT", obj=p0, args=(g, 100))


def test_elements_and_volume_add():
    import RF_Track
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    d = RF_Track.Drift(1.5)
    q = RF_Track.Quadrupole(0.2, 3.0)
    v = RF_Track.Volume()
    v.add(d, 0, 0, 0, 0, 0, 0)
    v.add(q, 0, 0, 1.5, 0, 0, 0)
    v2 = RF_Track.Volume()
    v2.add(RF_Track.Screen(), 0, 0, 0, 0, 0, 0)
    c = r.calls()
    _assert_one(c, "Drift", obj=d, args=(1.5,))
    _assert_one(c, "Quadrupole", obj=q, args=(0.2, 3.0))
    _assert_n(c, "Volume.add", 3)
    _assert_kinds_in_order(
        c, ["Drift", "Quadrupole", "Volume.add", "Volume.add", "Screen", "Volume.add"]
    )
    adds = [x for x in c if x.kind == "Volume.add"]
    # the first two belong to the same Volume (see map_elements()'s own
    # "only one Volume/Lattice is supported" check, in
    # rftrack_import_mapper.py, for why this matters), the third to a
    # different one entirely
    pkeq(id(v), adds[0].container_id)
    pkeq(id(v), adds[1].container_id)
    pkeq(id(v2), adds[2].container_id)


def test_errors_propagate():
    """A real RF_Track construction error (e.g. a bad keyword arg -- the
    bound constructors only accept positional args) must surface exactly
    as it would unwrapped, not be swallowed or altered by the recorder.
    """
    import RF_Track
    from pykern.pkunit import pkeq, pkexcept
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    with pkexcept(TypeError):
        RF_Track.Quadrupole(0.2, gradient=3.0)
    pkeq(0, len(r.calls()))


def test_install_resets():
    import RF_Track
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    RF_Track.Drift(1.0)
    pkeq(1, len(r.calls()))
    r.install()
    pkeq(0, len(r.calls()))


def test_lattice_append():
    import RF_Track
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    s = RF_Track.Screen()
    v = RF_Track.Lattice()
    v.append(s)
    _assert_one(r.calls(), "Lattice.append", obj=s)


def test_rbend_is_a_function():
    """RF_Track.RBend is a factory function (returning an RF_Track.SBend
    instance), not a class -- it has no __init__ to wrap, so it must go
    through _wrap_function like Bunch6d_QR, not _wrap_class like the other
    element types.
    """
    import RF_Track
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    e = RF_Track.RBend(0.5, 0.1, 938.272)
    pkeq(0.1, e.get_angle())
    _assert_one(r.calls(), "RBend", obj=e, args=(0.5, 0.1, 938.272))


def test_rescale_detection():
    """note_loadtxt_raw() + the next field-map class constructed records
    `ratio` (final/raw, exact for "factor" mode) and `peak`
    (max(abs(final)), exact for "peak" mode) on that same call -- for
    whichever mode actually ran, since both reduce to the same uniform
    scalar multiply of the raw array (see rftrack_import_recorder.
    _resolve_rescale()'s own docstring). Consumed and cleared either
    way, so an unrelated later construction never sees stale data.
    """
    import RF_Track
    import numpy
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    raw = numpy.array([0.0, 2.0, 4.0, 2.0, 0.0])
    r.note_loadtxt_raw(raw)
    final = raw * 0.5
    e = RF_Track.Static_Magnetic_FieldMap_1d(final, 0.1)
    c = [x for x in r.calls() if x.kind == "Static_Magnetic_FieldMap_1d"]
    pkeq(1, len(c))
    pkeq(0.5, c[0].rescale.ratio)
    pkeq(2.0, c[0].rescale.peak)

    # not stale: a construction with no preceding note_loadtxt_raw() at
    # all gets back None, not the previous call's leftover data
    e2 = RF_Track.Static_Magnetic_FieldMap_1d(final, 0.1)
    c2 = [x for x in r.calls() if x.kind == "Static_Magnetic_FieldMap_1d"][1]
    pkeq(None, c2.rescale)


def test_rescale_detection_mismatched_shape():
    """The raw array note_loadtxt_raw() was given doesn't line up with
    the field-map element's own final array at all (e.g. an arbitrary
    script's own column convention doesn't match the one this detection
    assumes) -- nothing reliable to report, not a guess.
    """
    import RF_Track
    import numpy
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    r.note_loadtxt_raw(numpy.array([1.0, 2.0, 3.0]))
    RF_Track.Static_Magnetic_FieldMap_1d(numpy.array([1.0, 2.0]), 0.1)
    c = r.calls()[-1]
    pkeq(None, c.rescale)


def test_rescale_detection_non_uniform_ratio():
    """final isn't a uniform scalar multiple of raw at all -- neither
    rescale mode produces this, so there's nothing honest to report.
    """
    import RF_Track
    import numpy
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    r.note_loadtxt_raw(numpy.array([1.0, 2.0, 3.0]))
    RF_Track.Static_Magnetic_FieldMap_1d(numpy.array([1.0, 5.0, 2.0]), 0.1)
    c = r.calls()[-1]
    pkeq(None, c.rescale)


def test_track_is_a_noop():
    """track() actually runs the numerical simulation -- arbitrarily
    expensive, and unnecessary for import, which only wants the
    lattice/bunch structure already built by the time a script starts
    tracking. Unlike an earlier design that raised to abort the whole
    script right here (on the assumption nothing useful ever follows a
    real generated script's one, final track() call), it's a no-op now,
    the same as autophase()/btrack() (see test_autophase_is_a_noop()) --
    a real hand-written script can track more than once (e.g. a cheap
    verification track, then real space-charge setup and tracking), and
    aborting at the first one used to discard all of that.
    """
    import RF_Track
    import numpy
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_recorder as r

    r.install()
    v = RF_Track.Volume()
    d = RF_Track.Drift(1.5)
    d.set_name("D1")
    d.set_aperture(0.02, 0.02, "circular")
    v.add(d, 0, 0, 0, 0, 0, 0)
    v.set_s0(0)
    v.set_s1(1.5)
    b = RF_Track.Bunch6d(
        0.511, 0.0, -1.0, numpy.array([0.0, 0.0, 0.0, 0.0, 0.0, 100.0])
    )
    pkeq(None, v.track(b))
    after = RF_Track.Drift(2.0)
    _assert_one(r.calls(), "Volume.track", obj=None, args=(b,))
    _assert_kinds_in_order(
        r.calls(),
        [
            "Drift",
            "Volume.add",
            "Volume.set_s0",
            "Volume.set_s1",
            "Bunch6d",
            "Volume.track",
            "Drift",
        ],
    )


def _assert_kinds_in_order(calls, kinds):
    from pykern.pkunit import pkeq

    pkeq(kinds, [c.kind for c in calls])


def _assert_n(calls, kind, count):
    from pykern.pkunit import pkeq

    pkeq(count, len([c for c in calls if c.kind == kind]))


def _assert_one(calls, kind, obj, args=(), kwargs=None):
    from pykern.pkunit import pkeq

    m = [c for c in calls if c.kind == kind]
    pkeq(1, len(m))
    pkeq(obj, m[0].obj)
    pkeq(args, m[0].args)
    pkeq(kwargs or {}, m[0].kwargs)
