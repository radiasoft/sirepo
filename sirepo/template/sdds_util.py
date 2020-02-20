# -*- coding: utf-8 -*-
u"""SDDS utilities.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.template import elegant_common
import math
import re
import sdds

# elegant mux and muy are computed in sddsprocess below
_ELEGANT_TO_MADX_COLUMNS = [
    ['ElementName', 'NAME'],
    ['ElementType', 'TYPE'],
    ['s', 'S'],
    ['betax', 'BETX'],
    ['alphax', 'ALFX'],
    ['mux', 'MUX'],
    ['etax', 'DX'],
    ['etaxp', 'DPX'],
    ['betay', 'BETY'],
    ['alphay', 'ALFY'],
    ['muy', 'MUY'],
    ['etay', 'DY'],
    ['etayp', 'DPY'],
    ['ElementOccurence', 'COUNT'],
]

MADX_TWISS_COLUMS = map(lambda row: row[1], _ELEGANT_TO_MADX_COLUMNS)

_SDDS_INDEX = 0


def extract_sdds_column(filename, field, page_index):
    return process_sdds_page(filename, page_index, _sdds_column, field)


def process_sdds_page(filename, page_index, callback, *args, **kwargs):
    try:
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, filename) != 1:
            pkdlog('{}: cannot access'.format(filename))
            # In normal execution, the file may not yet be available over NFS
            err = _sdds_error('Output file is not yet available.')
        else:
            #TODO(robnagler) SDDS_GotoPage not in sddsdata, why?
            for _ in xrange(page_index + 1):
                if sdds.sddsdata.ReadPage(_SDDS_INDEX) <= 0:
                    #TODO(robnagler) is this an error?
                    break
            try:
                return callback(*args, **kwargs)
            except SystemError as e:
                pkdlog('{}: page not found in {}'.format(page_index, filename))
                err = _sdds_error('Output page {} not found'.format(page_index) if page_index else 'No output was generated for this report.')
    finally:
        try:
            sdds.sddsdata.Terminate(_SDDS_INDEX)
        except Exception:
            pass
    return {
        'err': err,
    }


def twiss_to_madx(elegant_twiss_file, madx_twiss_file):
    outfile = 'sdds_output.txt'
    twiss_file = 'twiss-with-mu.sdds'
    # convert elegant psix to mad-x MU, rad --> rad / 2pi
    pksubprocess.check_call_with_signals([
        'sddsprocess',
        elegant_twiss_file,
        '-define=column,mux,psix 2 pi * /',
        '-define=column,muy,psiy 2 pi * /',
        twiss_file,
    ], output=outfile, env=elegant_common.subprocess_env())
    pksubprocess.check_call_with_signals([
        'sdds2stream',
        twiss_file,
        '-columns={}'.format(','.join(map(lambda x: x[0], _ELEGANT_TO_MADX_COLUMNS))),
    ], output=outfile, env=elegant_common.subprocess_env())
    lines = pkio.read_text(outfile).split('\n')
    header = '* {}\n$ \n'.format(' '.join(map(lambda x: x[1], _ELEGANT_TO_MADX_COLUMNS)))
    pkio.write_text(madx_twiss_file, header + '\n'.join(lines) + '\n')


def _safe_sdds_value(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0
    return v


def _sdds_column(field):
    column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
    column_def = sdds.sddsdata.GetColumnDefinition(_SDDS_INDEX, field)
    values = sdds.sddsdata.GetColumn(
        _SDDS_INDEX,
        column_names.index(field),
    )
    return PKDict(
        values=map(lambda v: _safe_sdds_value(v), values),
        column_names=column_names,
        column_def=column_def,
        err=None,
    )


def _sdds_error(error_text='invalid data file'):
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return PKDict(
        error=error_text,
    )
