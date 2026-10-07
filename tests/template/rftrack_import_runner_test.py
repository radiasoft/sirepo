"""PyTest for :mod:`sirepo.template.rftrack_import_runner`

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_elements_and_bunch():
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

v = rft.Volume()
v.add(rft.Drift(1.5), 0, 0, 0, 0, 0, 0)
v.add(rft.Quadrupole(0.2, 3.0), 0, 0, 1.5, 0, 0, 0)

g = rft.Bunch6dT_Generator()
g.species = "electron"
g.charge = -1.0
p0 = rft.Bunch6dT(g, 100)
"""
    )
    pkeq("ok", res.status)
    pkeq(
        ["Drift", "Volume.add", "Quadrupole", "Volume.add", "Bunch6dT_Generator"],
        [c.kind for c in res.calls[:-1]],
    )
    pkeq(1.5, res.calls[0].fields.get_length)
    pkeq("electron", res.calls[4].fields.species)
    pkeq(-1.0, res.calls[4].fields.charge)


def test_missing_dependency():
    from pykern.pkunit import pkexcept
    from sirepo.template import rftrack_import_runner

    with pkexcept("not available: some_totally_fake_package_xyz"):
        rftrack_import_runner.run("import some_totally_fake_package_xyz\n")


def test_no_rf_track_calls():
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run("import math\nx = math.sqrt(4)\n")
    pkeq("ok", res.status)
    pkeq([], res.calls)


def test_notebook_export_artifacts():
    """A `jupyter nbconvert --to script` export calls get_ipython() for
    any cell magic the notebook used, and commonly imports
    matplotlib.pyplot to plot the lattice -- neither should break import.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run(
        """
get_ipython().run_line_magic("matplotlib", "inline")
import matplotlib.pyplot as plt
import RF_Track as rft

v = rft.Volume()
v.add(rft.Drift(1.0), 0, 0, 0, 0, 0, 0)
plt.plot([1, 2, 3])
plt.show()
"""
    )
    pkeq("ok", res.status)
    pkeq(["Drift", "Volume.add"], [c.kind for c in res.calls])


def test_partial_error_tolerated_when_calls_exist():
    """A script that crashes after already building something useful
    (unlike test_script_exception's immediate `raise`, with nothing
    recorded at all) gets back `status="ok"` with whatever it built,
    plus `partial_error` naming what it never finished -- not a hard
    failure. This is what track()/btrack()/autophase() being no-ops
    instead of an abort actually relies on: a script that keeps running
    past them and then hits unrelated tail code (plotting, saving, a
    None "tracked bunch" being used as if it tracked something) doesn't
    lose the lattice/bunch/settings already captured.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run(
        """
import RF_Track as rft

v = rft.Volume()
v.add(rft.Drift(1.5), 0, 0, 0, 0, 0, 0)
raise ValueError("boom")
"""
    )
    pkeq("ok", res.status)
    pkeq(["Drift", "Volume.add"], [c.kind for c in res.calls])
    pkeq("boom", res.partial_error)


def test_pc_mev_absent_without_bunch_global():
    """An arbitrary hand-written script has no top-level BUNCH PKDict at
    all -- nothing to read, not a guess at some other value.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run("import RF_Track as rft\nrft.Drift(1.0)\n")
    pkeq("ok", res.status)
    pkeq(None, res.get("pc_mev"))


def test_pc_mev_recovered_from_bunch_global():
    """Only a script Sirepo itself generated defines a top-level BUNCH
    PKDict with a pc_mev key (see parameters.py.jinja) -- read back
    directly, bypassing RF_Track entirely, since pc has no execution
    trace at all for a Cathode bunch (see
    rftrack_import_driver._resolve_pc_mev()).
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run(
        """
from pykern.pkcollections import PKDict
import RF_Track as rft

BUNCH = PKDict(pc_mev=42.0, mass_mev=0.511)
rft.Drift(1.0)
"""
    )
    pkeq("ok", res.status)
    pkeq(42.0, res.pc_mev)


def test_pc_mev_survives_script_exception():
    """BUNCH is assigned at the script's top level, before main() ever
    runs -- it's already in the driver's own globals dict regardless of
    whether the rest of the script goes on to raise partway through
    (tolerated here since the lattice was already built -- see
    test_partial_error_tolerated_when_calls_exist), which is why this
    driver keeps its own reference to that dict instead of relying on
    runpy.run_path()'s return value (unreachable once an exception
    propagates out of the run).
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    res = rftrack_import_runner.run(
        """
from pykern.pkcollections import PKDict
import RF_Track as rft

BUNCH = PKDict(pc_mev=7.5)
v = rft.Volume()
v.add(rft.Drift(1.5), 0, 0, 0, 0, 0, 0)
raise ValueError("boom")
"""
    )
    pkeq("ok", res.status)
    pkeq(7.5, res.pc_mev)
    pkeq("boom", res.partial_error)


def test_script_exception():
    from pykern.pkunit import pkexcept
    from sirepo.template import rftrack_import_runner

    with pkexcept("script raised: boom"):
        rftrack_import_runner.run('raise ValueError("boom")\n')


def test_timeout():
    from pykern.pkunit import pkexcept
    from sirepo.template import rftrack_import_runner

    rftrack_import_runner._cfg.timeout_secs = 1
    with pkexcept("exceeded 1s timeout"):
        rftrack_import_runner.run("import time\ntime.sleep(10)\n")


def test_track_is_a_noop():
    """track() doesn't actually run the numerical simulation this import
    doesn't need (same as autophase()/btrack()) -- but, unlike an
    earlier design that aborted the whole script right at track()
    (on the assumption nothing useful ever follows a real generated
    script's one, final track() call), it's a no-op now, specifically
    so a script that tracks more than once for its own reasons -- e.g.
    a cheap autophase-verification track, *then* space-charge setup,
    *then* the real tracked-bunch run -- keeps going instead of losing
    everything after the first one. Whatever runs after a no-op'd
    track() is bounded only by the subprocess's own timeout (see
    test_timeout), not by an immediate abort at the call itself.
    """
    from pykern.pkunit import pkeq
    from sirepo.template import rftrack_import_runner

    # not left over from test_timeout's own 1s override -- too short for
    # this subprocess's own startup+RF_Track-import overhead
    rftrack_import_runner._cfg.timeout_secs = 30
    res = rftrack_import_runner.run(
        """
import RF_Track as rft
import numpy

v = rft.Volume()
v.add(rft.Drift(1.5), 0, 0, 0, 0, 0, 0)
v.set_s0(0)
v.set_s1(1.5)
b = rft.Bunch6d(0.511, 0.0, -1.0, numpy.array([0.0, 0.0, 0.0, 0.0, 0.0, 100.0]))
tracked = v.track(b)
after = rft.Drift(2.0)
"""
    )
    pkeq("ok", res.status)
    pkeq(
        [
            "Drift",
            "Volume.add",
            "Volume.set_s0",
            "Volume.set_s1",
            "Bunch6d",
            "Volume.track",
            "Drift",
        ],
        [c.kind for c in res.calls],
    )
