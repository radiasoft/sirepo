"""test cortex isotopic pathway analysis

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest

pytest.importorskip("openmc_pathway_analysis")

_CHAIN = """<?xml version="1.0"?>
<depletion_chain>
  <nuclide name="U235" decay_modes="0" reactions="1">
    <reaction type="fission" Q="0.0"/>
    <neutron_fission_yields>
      <energies>2.53000e-02</energies>
      <fission_yields energy="2.53000e-02">
        <products>I135 Xe135</products>
        <data>0.06 0.01</data>
      </fission_yields>
    </neutron_fission_yields>
  </nuclide>
  <nuclide name="I135" decay_modes="1" reactions="1" half_life="2.36520E+04">
    <decay type="beta" target="Xe135" branching_ratio="1.0"/>
    <reaction type="(n,gamma)" Q="0.0" target="Xe136" branching_ratio="1.0"/>
  </nuclide>
  <nuclide name="Xe135" decay_modes="0" reactions="0"/>
  <nuclide name="Xe136" decay_modes="0" reactions="0"/>
</depletion_chain>
"""

#: depletion material id of the First_Wall layer
_MAT_ID = "18"


def test_pathway_analysis():
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo import srunit
    import sirepo.sim_data
    import sirepo.simulation_db
    import sirepo.template.cortex

    s = sirepo.sim_data.get_class("cortex")
    with srunit.quest_start(want_user=True) as qcall:
        # not empty, the work dir has the user's db
        with pkunit.save_chdir_work(want_empty=False):
            for k, v in write_inputs(pkunit.work_dir().join("inputs")).items():
                s.lib_file_write(s.pathway_lib_file(k), v, qcall=qcall)
            # not in an agent, so lib_file_abspath needs the user
            sirepo.simulation_db._cfg.logged_in_user = qcall.auth.logged_in_user()

            def _compute(**kwargs):
                return sirepo.template.cortex.stateless_compute_pathway_analysis(
                    PKDict(
                        args=PKDict(
                            layer="First_Wall",
                            metric="activity",
                            by_element=False,
                            cooling_seconds=100 * y,
                            stamp="stamp1",
                        ).pkupdate(kwargs),
                    ),
                )

            def _nuclide(nuclide):
                return sirepo.template.cortex.stateless_compute_pathway_nuclide(
                    PKDict(
                        args=PKDict(
                            layer="First_Wall",
                            nuclide=nuclide,
                            cooling_seconds=100 * y,
                            stamp="stamp2",
                        ),
                    ),
                )

            y = sirepo.template.cortex._SECONDS_PER_YEAR
            r = _compute()
            pkunit.pkeq("First_Wall", r.layer)
            pkunit.pkeq("Bq/kg", r.units)
            pkunit.pkeq(100 * y, r.coolingSeconds)
            # the nearest step, shutdown, since the results have no step at 1 day
            pkunit.pkeq(0, _compute(cooling_seconds=86_400).coolingSeconds)
            pkunit.pkeq(["I135"], [x.name for x in r.rows])
            pkunit.pkeq(100.0, round(sum(x.percent for x in r.rows), 6))
            pkunit.pkeq(round(r.total, 12), round(sum(x.value for x in r.rows), 12))
            # the final nuclides which carry the activity
            pkunit.pkeq("I135", r.radionuclides[0].name)
            pkunit.pkeq(100.0, round(sum(x.percent for x in r.radionuclides), 6))
            pkunit.pkre(r"^Class", r.wasteClass)
            pkunit.pkeq(
                ["I"],
                [x.name for x in _compute(by_element=True).rows],
            )
            pkunit.pkeq(None, _compute(metric="waste_disposal_rating").units)
            # target_origins solves once per graph, see _pathway_patch
            import openmc_pathway_analysis.production_graph

            pkunit.pkok(
                openmc_pathway_analysis.production_graph.compute_absorption_probabilities.sr_is_cached,
                "compute_absorption_probabilities not patched",
            )
            # the loaded inputs are kept for the same stamp
            p = sirepo.template.cortex._pathway.pathways
            _compute(metric="decay_heat")
            pkunit.pkok(
                p is sirepo.template.cortex._pathway.pathways,
                "inputs reloaded for the same stamp",
            )
            _compute(stamp="stamp2")
            pkunit.pkok(
                p is not sirepo.template.cortex._pathway.pathways,
                "inputs not reloaded for a new stamp",
            )
            with pkunit.pkexcept("invalid metric"):
                _compute(metric="nope")
            with pkunit.pkexcept("invalid cooling_seconds"):
                _compute(cooling_seconds=60)
            with pkunit.pkexcept("not in the material map"):
                _compute(layer="Armor")
            # production pathway of a final nuclide
            r = _nuclide("Xe135")
            pkunit.pkeq("Xe135", r.nuclide)
            pkunit.pkeq(r.origins[0].name, r.chain[0].name)
            pkunit.pkeq(None, r.chain[0].channel)
            pkunit.pkeq("Xe135", r.chain[-1].name)
            pkunit.pkok(r.chain[-1].channel, "no channel to the nuclide")
            # in the material from the start
            r = _nuclide("I135")
            pkunit.pkeq(["I135"], [x.name for x in r.chain])
            with pkunit.pkexcept("invalid nuclide"):
                _nuclide("../x")


def write_inputs(directory):
    """Pathway analysis inputs with the First_Wall layer, see SimData.PATHWAY_FILES

    Args:
        directory (py.path): created if it doesn't exist
    Returns:
        PKDict: path by key of PATHWAY_FILES
    """
    from pykern import pkio
    from pykern.pkcollections import PKDict
    import sirepo.sim_data

    pkio.mkdir_parent(directory)
    rv = PKDict(
        {
            k: directory.join(v)
            for k, v in sirepo.sim_data.get_class("cortex").PATHWAY_FILES.items()
        }
    )
    rv.chain.write(_CHAIN)
    rv.material_map.write(
        "cell_id,mat_id,material_name,chunk_key,volume_cm3\n"
        + f"67,{_MAT_ID},First_Wall,OB_1_b6,1.0\n",
    )
    _results(rv.results)
    return rv


def _results(path):
    """depletion_results.h5 of one material: a source, shutdown, then 100 years

    Like openmc-pathway-analysis tests/fixtures/make_simple_results.py
    """
    import h5py
    import numpy
    import sirepo.template.cortex

    y = sirepo.template.cortex._SECONDS_PER_YEAR
    n = ["U235", "I135", "Xe135"]
    x = ["fission", "(n,gamma)"]
    t = numpy.array(
        [[0.0, 10.0], [10.0, 10.0 + 100 * y], [10.0 + 100 * y, 10.0 + 100 * y]],
    )
    a = numpy.zeros((len(t), 1, len(n)))
    a[:, 0, 0] = 100.0
    a[:, 0, 1] = 5.0
    r = numpy.zeros((len(t), 1, len(n), len(x)))
    r[0, 0, 0, 0] = 1.0
    r[0, 0, 1, 1] = 0.1
    with h5py.File(str(path), "w") as f:
        f.attrs["filetype"] = numpy.bytes_("depletion results")
        f.attrs["version"] = numpy.array([1, 2], dtype=int)
        f.create_dataset("time", data=t)
        f.create_dataset("number", data=a)
        f.create_dataset("reaction rates", data=r)
        f.create_dataset("eigenvalues", data=numpy.zeros((len(t), 2)))
        f.create_dataset("depletion time", data=numpy.zeros(len(t)))
        # shutdown at step 1
        f.create_dataset("source_rate", data=numpy.array([1.0, 0.0, 0.0]))
        g = f.create_group("materials").create_group(_MAT_ID)
        g.attrs["index"] = 0
        g.attrs["volume"] = 1.0
        g = f.create_group("nuclides")
        for i, v in enumerate(n):
            g.create_group(v).attrs.update(
                {"atom number index": i, "reaction rate index": i}
            )
        g = f.create_group("reactions")
        for i, v in enumerate(x):
            g.create_group(v).attrs["index"] = i
