import os
import sys
import re
import subprocess
from pykern import pkunit
from pykern import pksetup
from pykern import pkio
from pykern.pkdebug import pkdp

_RENAMER_EXCLUDE_FILES = re.compile(
    f".*{pkunit.WORK_DIR_SUFFIX}/"
    + r"|.*(_console\.py)|^venv/"
    + r"|^run/"
    + r"|__pycache__/ "
    + r"|\/js\/ext"
    + r"|^.*\.(git|cache)|node_modules"
    + r"|^.*\.(sdds|bun|png|jpg|woff|eot|ttf|tif|gif|ico|h5m|zip|log|db|csv|h5|stl|dat|log|npy|pyc|paramOpt|gz|woff2)$"
)


def rename_app(old_app_name, new_app_name):
    _Renamer(old_app_name, new_app_name).rename()


class _Renamer:
    def __init__(self, old_app_name, new_app_name):
        self.old_app_name = old_app_name
        self.new_app_name = new_app_name
        self.exclude_files = _RENAMER_EXCLUDE_FILES

    def _iterate(self, rename_function, dirs=False):
        for f in pkio.walk_tree("./"):
            if self._exclude(f, dirs):
                continue
            rename_function(f)

    def _rename_paths(self):
        # rename base and dirnames
        self._iterate(self._rename_file)
        self._iterate(self._rename_dir, dirs=True)

    def _rename_file(self, file_path):
        if self.old_app_name in file_path.basename:
            d = str(file_path.dirname)
            b = str(file_path.basename)
            os.rename(
                str(file_path),
                d + "/" + b.replace(self.old_app_name, self.new_app_name),
            )

    def _rename_dir(self, file_path):
        if self.old_app_name in file_path.dirname:
            self._dir(str(file_path.dirname))

    def _dir(self, dir):
        if os.path.exists(dir):
            t = ""
            for piece in dir.split("/"):
                t += f"/{piece}"
                if self.old_app_name in piece:
                    break
            os.rename(t, t.replace(self.old_app_name, self.new_app_name))

    def _rename_references(self):
        self._replace_references()
        self._raise_for_references()

    def _exclude(self, file, dirs):
        return re.search(self.exclude_files, pkio.py_path().bestrelpath(file))

    def _replace_references(self):
        for f in pkio.walk_tree("./"):
            if self._exclude(f, False):
                continue
            with pkio.open_text(f) as t:
                t = t.read()
                self._replace(f, t)

    def _replace(self, file, text):
        if re.search(re.compile(self.old_app_name), text):
            # TODO (gurhar1133): re.sub instead?
            pkio.write_text(
                file,
                text.replace(
                    self.old_app_name,
                    self.new_app_name,
                )
                .replace(
                    self.old_app_name.title(),
                    self.new_app_name.title(),
                )
                .replace(
                    self.old_app_name.upper(),
                    self.new_app_name.upper(),
                ),
            )

    def _raise_for_references(self):
        o = (
            subprocess.check_output(
                [
                    "grep",
                    "-r",
                    "-i",
                    "-I",
                    "--exclude-dir='.pytest_cache'",
                    "--exclude='./x.py'",
                    "--exclude-dir='sirepo.egg-info'",
                    f"{self.old_app_name}",
                ]
            )
            .decode("utf-8")
            .split("\n")[:-1]
        )
        r = []
        for line in o:
            if not re.search(self.exclude_files, line.split(":")[0]):
                r.append(line)
        if len(r) > 0:
            m = "\n".join(r)
            raise AssertionError(
                f"{m}\n{len(r)} REFERENCES TO {self.old_app_name} FOUND"
            )

    def rename(self):
        self._rename_paths()
        self._rename_references()
