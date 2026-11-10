"""utilities for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import csv
import io
import openpyxl
import os
import pykern.pkio
import pykern.pkjson
import re
import requests
import sirepo.auth
import sirepo.mpi
import sirepo.quest
import sirepo.resource
import sirepo.sim_api.cortex
import sirepo.template.cortex
import sirepo.template.template_common
import subprocess
import tempfile

_CENTURY = 100.0 * 365 * 24 * 60 * 60


def build_slab_jinja(src_dir):
    """Rebuild cortex's slab.py.jinja from the full_model_bluemira sources

    `src_dir` holds the standalone neutronics scripts (inputs.py,
    eudemo_materials.py, geometry.py, neutronics_model.py, neutronics_post.py,
    depletion_model.py, depletion_post.py). slab.py.jinja is those files
    concatenated in a fixed order, each put through a stored patch
    (`sirepo/package_data/template/cortex/slab_src_patches/<name>.patch`)
    that captures the hand edits needed to turn a standalone script into a
    chunk of the merged template (jinja variables such as
    ``BREEDER_TYPE = "{{ slabType }}"``, commenting out each file's own
    ``import inputs as cfg`` in favor of a shared globals() namespace, etc).

    Run this whenever a full_model_bluemira source file changes. If a file
    changed in a way that no longer matches its patch's context lines,
    `patch` fails loudly (leaving a `.rej` file) rather than silently
    producing a wrong merge -- reconcile by hand, then regenerate that one
    patch from the resolved chunk, e.g.::

        diff -u src_dir/inputs.py resolved_chunk.py \\
            | sed '1s#.*#--- a/inputs.py#;2s#.*#+++ b/inputs.py#' \\
            > slab_src_patches/inputs.py.patch

    Args:
        src_dir (str): path to the full_model_bluemira directory
    """

    def _slab_jinja_patch(src_dir, patch_dir, name):
        d = pykern.pkio.py_path(tempfile.mkdtemp())
        t = d.join(name)
        src_dir.join(name).copy(t)
        subprocess.check_call(
            # -l: ignore whitespace-only drift (e.g. trailing space stripped
            # by a formatter) so only real content conflicts fail the patch
            ["patch", "-l", "-p1", "-i", str(patch_dir.join(name + ".patch"))],
            cwd=str(d),
        )
        return pykern.pkio.read_text(t)

    # order full_model_bluemira source files are merged into slab.py.jinja;
    # `None` marks a literal chunk (`_glue`) that isn't derived from any
    # source file
    _sources = (
        "inputs.py",
        "eudemo_materials.py",
        "geometry.py",
        "neutronics_model.py",
        None,
        "neutronics_post.py",
        "depletion_model.py",
        "depletion_post.py",
    )
    _preamble = "\n{{ materialDefinition }}\n\n"
    _banner = "# " + "*" * 77 + "\n"
    _glue = "STATEPOINT_FILE = rsrun(model.run())\n\n\n"

    s = pykern.pkio.py_path(src_dir)
    p = sirepo.resource.file_path("template", "cortex", "slab_src_patches")
    o = [_preamble]
    for n in _sources:
        o.append(_banner)
        o.append(_glue if n is None else _slab_jinja_patch(s, p, n))
    t = sirepo.resource.file_path("template", "cortex", "slab.py.jinja")
    pykern.pkio.write_text(t, "".join(o))
    return t


def create_reference_xlsx(xlsx_template_filename, compendium_filename):

    _COMPONENT_ROW = 18

    # This is for the mapping for the default template XLSX file in package_data lib
    _COMMENT_ROWS = PKDict(
        density_comments=7,
        composition_comments=13,
    )
    _FIELD_TO_LOCATION = PKDict(
        {
            "Metadata and Settings": PKDict(
                name="B3",
                material_type="B4",
                availability_factor="B12",
                homogenized_hcpb="B19",
            ),
            "Composition": PKDict(
                url="B3",
                source="B4",
                pointer="B5",
                density_g_cc="B6",
                density_comments=f"B{_COMMENT_ROWS.density_comments}",
                composition_comments=f"B{_COMMENT_ROWS.composition_comments}",
            ),
        }
    )

    def _classify_references(references):
        d = PKDict(url="", pointer="", density_comments="", composition_comments="")
        for r in references:
            # fix missing URL prefix
            for m in re.findall(r"\s\(?(\w+\.\w+\.\w\S*?\/\w\S*?)", r):
                r = r.replace(m, f"https://{m}")
            if "density" in r.lower() or re.search(r"^http\S+$", r):
                m = re.search(r"(http.*?)(?:\s|$)", r, re.IGNORECASE)
                if m and not d.url:
                    d.url = re.sub(r"[.),]*$", "", str(m.group(1)))
                    # only get pointer from first reference
                    m = re.search(
                        r"\b(table|page|figure)\s+(\d.*?),?\s", r, re.IGNORECASE
                    )
                    if m:
                        d.pointer = f"{m.group(1)[0].upper()}{m.group(2)}"
                d.density_comments += (" " if d.density_comments else "") + r
            elif "isotop" in r.lower():
                d.composition_comments += (" " if d.composition_comments else "") + r
        return d

    def _comment(json_data):
        if "Comment" in json_data:
            if isinstance(json_data.Comment, list):
                return json_data.Comment
            return [json_data.Comment]
        return []

    def _create_xlsx(values):
        pkdlog("creating: {}", values.name)
        wb = openpyxl.load_workbook(xlsx_template_filename)
        for n in _FIELD_TO_LOCATION:
            ws = wb[n]
            for f, c in _FIELD_TO_LOCATION[n].items():
                ws[c] = values[f]
        for f, r in _COMMENT_ROWS.items():
            if values[f]:
                # increase cell height if comments are present
                wb["Composition"].row_dimensions[r].height = 100
        for idx in range(len(values.nuclides)):
            c = values.nuclides[idx]
            row = idx + _COMPONENT_ROW
            ws[f"A{row}"] = re.sub(r"-", "", c.isotope)
            ws[f"E{row}"] = c.atom_fraction
        n = re.sub(r"\s+", "_", re.sub(r"[^a-zA-Z0-9 ]", " ", values.name).strip())
        wb.save(f"{n}.xlsx")

    for d in pykern.pkjson.load_any(pykern.pkio.read_text(compendium_filename)).data:
        v = PKDict(
            availability_factor="",
            density_g_cc=d.Density,
            homogenized_hcpb="NO",
            material_type="plasma-facing",
            name=d.Name,
            nuclides=[],
            source="",
        ).pkupdate(_classify_references(_comment(d) + d.References))
        for e in d.Elements:
            for i in e.Isotopes:
                v.nuclides.append(
                    PKDict(
                        isotope=i.Isotope,
                        atom_fraction=i.AtomFraction_whole * 100,
                    )
                )
        _create_xlsx(v)


def gen_components():

    def _livechart_csv():
        r = requests.get(
            "https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all"
        )
        r.raise_for_status()
        return io.StringIO(r.text)

    def _parse():
        rv = PKDict(elements=set(), nuclides=set())
        first = True
        for r in csv.reader(_livechart_csv()):
            if not r:
                continue
            if first:
                first = False
                continue
            # num protons
            z = int(r[0])
            if z <= 0:
                continue
            symbol = r[2]
            rv.elements.add(symbol)
            # half_life or from stephen:
            # "Actually, there may be some short-lived lithium isotopes that may be embedded in 1st wall materials, so let’s include all the Lithiums"
            if r[12] != "STABLE" and symbol != "Li":
                # half_life_sec
                if r[16] in ("", "?") or float(r[16]) < _CENTURY:
                    continue
            rv.nuclides.add(r[2] + str(int(r[1]) + z))
        # additional nuclides needed by PNNL examples
        for x in ("Pu238", "Pu241", "Ta180"):
            rv.nuclides.add(x)
        return rv

    def _to_str(components):
        rv = "_COMPONENTS = PKDict(\n"
        i = " " * 4
        j = i * 2
        for c in sorted(components.keys()):
            rv += i + c + "={\n"
            for n in sorted(components[c]):
                rv += f'{j}"{n}",\n'
            rv += i + "},\n"
        return rv + ")\n"

    return _to_str(_parse())


def import_xlsx(uid_or_email, *args):
    sirepo.sim_api.cortex.material_db.init_module()

    def _import_xlsx(filename):
        pkdlog("import: {}", filename)
        p = sirepo.sim_api.cortex.material_xlsx.Parser(filename)
        if p.errors:
            raise AssertionError(
                f"XLSX import {filename} failed with errors: {p.errors}"
            )
        sirepo.sim_api.cortex.material_db.insert_material(parsed=p.result, uid=u)

    if not len(args):
        pykern.pkcli.command_error("missing xlsx file names")
    with sirepo.quest.start() as qcall:
        u = qcall.auth.unchecked_get_user(uid_or_email)
        if not u:
            pykern.pkcli.command_error(f"invalid uid_or_email: {uid_or_email}")
        with qcall.auth.logged_in_user_set(u, method=sirepo.auth.METHOD_EMAIL):
            for f in args:
                _import_xlsx(f)


def run_background(cfg_dir):
    # TODO(pjm): must run as a separate process or OMP_NUM_THREADS will already
    #  be cached in libgomp with the wrong value
    pksubprocess.check_call_with_signals(
        ["python", sirepo.template.template_common.PARAMETERS_PYTHON_FILE],
        msg=pkdlog,
        output=sirepo.template.cortex.CORTEX_RUN_LOG,
        env=PKDict(os.environ).pkupdate(
            OMP_NUM_THREADS=str(sirepo.mpi.cfg().cores),
        ),
    )


def set_material_featured(material_id, is_featured, uid):
    sirepo.sim_api.cortex.material_db.init_module()
    sirepo.sim_api.cortex.material_db.set_featured(
        material_id, bool(int(is_featured)), uid
    )


def set_material_public(material_id, is_public, uid):
    sirepo.sim_api.cortex.material_db.init_module()
    sirepo.sim_api.cortex.material_db.set_public(material_id, bool(int(is_public)), uid)
