"""transliterate elegant manual into sirepo schema format

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkio, pkjson, pkconst
import re
import sirepo.const
import sirepo.resource
import subprocess


def parse_manual():
    return _Translate().out


class _Translate:
    def __init__(self):
        h = "ops.aps.anl.gov"
        self.in_dir = pkio.py_path(h)
        self.uri = f"https://{h}/manuals/elegant_latest/elegant.html"
        self.out = ""
        self.files = {}
        self.models = {}
        self.schema_file = sirepo.resource.static(
            "json", f"elegant-schema{sirepo.const.JSON_SUFFIX}"
        )
        self.schema = pkjson.load_any(self.schema_file)
        self._download()
        self._parse()
        self._models()
        self._views()
        self._types()

    def _download(self):
        if self.in_dir.exists():
            pkdlog("using existing: {}", self.in_dir)
            return
        pkdlog("downloading {}", self.uri)
        subprocess.run(
            f"wget --quiet --recursive --no-clobber --page-requisites --html-extension --convert-links --domains ops.aps.anl.gov --no-parent {self.uri}",
            shell=True,
        )

    def _models(self):
        for name in sorted(self.models):
            m = None
            if name.upper() == name:
                m = name
            else:
                m = f"command_{name}"
            if m in self.schema.model:
                print_header = False
                for f in self.models[name]:
                    if f == "printout_format":
                        continue
                    if m == "command_link_elements" and f == "minimium":
                        continue
                    if m == "command_load_parameters" and f == "filename_list":
                        continue
                    if m == "command_optimization_setup" and re.search(
                        "interrupt_file", f
                    ):
                        continue
                    if m == "command_run_setup" and f in (
                        "rootname",
                        "semaphore_file",
                        "search_path",
                    ):
                        continue
                    if m == "command_sdds_beam" and f == "input_list":
                        continue
                    if m == "command_track" and f == "interrupt_file":
                        continue
                    if f not in self.schema.model[m]:
                        if m == "BRAT" and f == "method":
                            continue
                        if m == "command_global_settings" and re.search(r"mpi", f):
                            continue
                        if not print_header:
                            print_header = True
                            self._out(f"{m} {self._unchecked_file(name)}")
                        self._out(f" + {f}")
                for f in self.schema.model[m]:
                    if m == "command_link_elements" and f == "minimum":
                        continue
                    if m == "command_track" and f in (
                        "use_linear_chromatic_matrix",
                        "longitudinal_ring_only",
                    ):
                        continue
                    if m == "command_tune_shift_with_amplitude" and f == "sparse_grid":
                        continue
                    if f == "name":
                        continue
                    if f not in self.models[name]:
                        if re.search(r"[a-z](X|Y)$", f):
                            continue
                        if not print_header:
                            print_header = True
                            self._out(f"{m} {self._unchecked_file(name)}")
                        self._out(f" - {f}")
            else:
                if m in ("command_semaphores", "command_subprocess"):
                    continue
                self._out(f"{m} {self._unchecked_file(name)}")
                self._out(f"{m} {self.files[name]}")
                for f in self.models[name]:
                    self._out(f" {f}")

    def _out(self, line):
        self.out += line + "\n"

    def _parse(self):
        for html_file in pkio.sorted_glob(
            self.in_dir.join("manuals/elegant_latest/*.html")
        ):
            name = None
            with pkio.open_text(html_file, encoding="cp1252") as f:
                text = f.read()
            state = "name"
            fields = []
            for line in text.split("\n"):
                if state == "name":
                    m = re.match(r".*<title>\s*(.*?)(\&.*)?\s*(</title>.*|$)", line)
                    if m:
                        name = m.group(1)
                        if " " in name:
                            continue
                        if name in ("HKPOLY", "bunched_beam_moments", "SCRIPT"):
                            continue
                        self.files[name] = html_file
                        assert name not in self.models, f"duplicate name: {name}"
                        self.models[name] = fields
                        state = "field_start"
                    continue
                if state == "field_start":
                    if re.search("^&amp;{}".format(name), line):
                        state = "fields"
                    # class="td11">Parameter Name </td><td  style="white-space:nowrap; text-align:left;" id="TBL-120-1-2"
                    elif re.search(r">Parameter Name\s*<", line):
                        state = "table_fields"
                    continue
                if state == "fields":
                    # &#x00A0;<br />&amp;end
                    if re.search(r">&amp;end$", line):
                        state = "done"
                    else:
                        # &#x00A0;<br />&#x00A0;&#x00A0;&#x00A0;&#x00A0;STRING&#x00A0;bunch&#x00A0;=&#x00A0;NULL;
                        line = re.sub(r"&#x00A0;", " ", line)
                        line = re.sub(r".*?<br />", "", line)
                        line = re.sub(r"^\s+", "", line)
                        if not line:
                            continue
                        f = line.split(" ")[1]
                        assert f, f"line split failed: {line}"
                        if (
                            f in ("balance_terms", "output_monitors_only")
                            and f in fields
                        ):
                            continue
                        assert f not in fields, f"duplicate field: {name} {f}"
                        f = re.sub(r"\[.*", "", f)
                        f = re.sub(r";", "", f)
                        if f == "removed_pegged":
                            f = "remove_pegged"
                        fields.append(f)
                    continue
                if state == "table_fields":
                    if re.search(r'class="td11">\s+</td></tr></table></div>', line):
                        state = "field_start"
                    else:
                        m = re.match(
                            '^class="td11">([a-zA-Z]\S*?)\s*</td>.*?style="white-space:nowrap; text-align:left;".*$',
                            line,
                        )
                        if m:
                            f = m.group(1)
                            if f == "STRING":
                                continue
                            if f.upper() == f:
                                assert f, f"line split failed: {line}"
                                assert (
                                    f not in fields
                                ), f"duplicate field: {name} {f}: {line}"
                                fields.append(f.lower())
            assert name
            if name in self.models and not self.models[name]:
                del self.models[name]

    def _types(self):
        for m in self.schema.model:
            if m == "_COMMAND":
                continue
            if m.upper() == m or re.search(r"^command_", m):
                for f in self.schema.model[m]:
                    if f in ("_super",) or re.search(r"(X|Y)$", f):
                        continue
                    assert (
                        f in self.schema.view[m].advanced
                    ), f"missing view field {m} {f}"

            def _types(self):
                _IGNORE_TOOLTIP_FIELDS = set(
                    [
                        "name",
                        "_super",
                        "malign_method",
                        "yaw_end",
                        "distribution",
                    ]
                )

                types = {}
                for m in self.schema.model:
                    if m == "_COMMAND":
                        continue
                    if m.upper() == m or re.search(r"^command_", m):
                        for f in self.schema.model[m]:
                            row = self.schema.model[m][f]
                            if f not in _IGNORE_TOOLTIP_FIELDS and not re.search(
                                r"(X|Y)$", f
                            ):
                                assert len(row) >= 4, f"missing tooltip: {m} {f}"
                            t = row[1]
                            assert not re.search(
                                r"^\d", str(t)
                            ), f"invalid type: {m} {f} {t}"
                            types[t] = True

                self._out("types:\n {}".format("\n ".join(sorted(types.keys()))))

    def _unchecked_file(self, name):
        return self.files.get(name, "none")

    def _views(self):
        for view in self.schema.view:
            if view.upper() == view or re.search(r"^command_", view):
                for f in self.schema.view[view].advanced:
                    assert f in self.schema.model[view], f"missing {view} {f}"
