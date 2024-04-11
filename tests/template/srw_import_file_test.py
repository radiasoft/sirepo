# -*- coding: utf-8 -*-
"""sipepo.importer test

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_import_json(fc):
    _do(fc, "json", lambda f: f.read(mode="rb"))


def test_import_python(fc):
    _do(fc, "py", lambda f: f.read(mode="rb"))


def test_import_zip(fc):
    import zipfile

    def _parse(fn):
        z = zipfile.ZipFile(str(fn))
        json = ""
        try:
            with z.open("sirepo-data.json") as f:
                json = f.read()
        except Exception:
            pass
        return json

    _do(fc, "zip", _parse)


def _do(fc, file_ext, parse):
    from pykern.pkcollections import PKDict
    from pykern import pkio, pkcompat
    from pykern import pkjson
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog
    from pykern.pkunit import pkeq, pkok, pkre
    import re

    for suffix in ("",) if file_ext == "py" else ("", " 2", " 3"):
        for f in pkio.sorted_glob(pkunit.data_dir().join("*." + file_ext)):
            pkdlog("file={}", f)
            json = pkcompat.from_bytes(parse(f))
            sim_type = re.search(r"^([a-z]+)_", f.basename).group(1)
            fc.sr_get_root(sim_type)
            is_dev = "deviance" in f.basename
            res = fc.sr_post_form(
                "importFile",
                PKDict(folder="/importer_test"),
                PKDict(simulation_type=sim_type),
                file=f,
            )
            if is_dev:
                m = re.search(r"Error: (.+)", json)
                if m:
                    expect = m.group(1)
                    pkre(expect, res.error)
                continue
            elif file_ext == "py":
                sim_name = f.purebasename
            else:
                sim_name = pkjson.load_any(json).models.simulation.name
            pkok("models" in res, "no models file={} res={}", f, res)
            pkeq(sim_name + suffix, res.models.simulation.name)
