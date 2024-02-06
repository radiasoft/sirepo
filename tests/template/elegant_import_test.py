"""Test elegant importer directly

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_importer():
    from pykern.pkcollections import PKDict
    from sirepo import template, srunit
    import sirepo.lib
    from pykern import pkio, pkunit, pkdebug

    for fn in pkio.sorted_glob(pkunit.data_dir().join("*")):
        if not pkio.has_file_extension(fn, ("ele", "lte")) or fn.basename.endswith(
            ".ele.lte"
        ):
            continue
        k = PKDict()
        pkdebug.pkdlog("file={}", fn)
        if fn.basename.startswith("deviance-"):
            try:
                # Do not try to look at imported_data, because
                # the exception should happen inside the import
                srunit.template_import_file("elegant", fn)
            except Exception as e:
                k.actual = f"{e}\n"
            else:
                k.actual = "did not raise exception"
        elif fn.ext == ".lte":
            data = srunit.template_import_file("elegant", fn).imported_data
            g = sirepo.template.import_module("elegant")._Generate(data)
            g.sim()
            j = g.jinja_env
            k.actual = j.rpn_variables + j.lattice
        else:
            f = (
                sirepo.lib.Importer("elegant")
                .parse_file(fn)
                .write_files(pkunit.work_dir())
            )
            k.actual_path = f.commands
        pkunit.file_eq(fn.basename + ".txt", **k)
