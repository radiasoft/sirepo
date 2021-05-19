# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc


def test_import():
    from pykern import pkjson
    from pykern.pkunit import pkeq
    from sirepo.template import flash_parser
    import re

    def _parse_config(fn):
        return flash_parser.ConfigParser().parse(pkio.read_text(fn))

    def _parse_par(fn):
        data_file = fn.basename.replace('-flash.par', '')
        return flash_parser.ParameterParser().parse(
            pkjson.load_any(pkio.read_text(pkunit.data_dir().join(f'{data_file}-sirepo-data.json'))),
            pkio.read_text(fn),
        )

    with pkunit.save_chdir_work():
        for fn in pkio.sorted_glob(pkunit.data_dir().join('*')):
            if re.search(r'-Config$', fn.basename):
                parser = _parse_config
            elif re.search(r'flash.par$', fn.basename):
                parser = _parse_par
            else:
                continue
            try:
                actual = pkjson.dump_pretty(parser(fn))
            except Exception as e:
                pkdlog(pkdexc())
                actual = str(e)
            outfile = f'{fn.basename}.out'
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            pkeq(expect, actual)
