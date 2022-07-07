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
import threading

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

# start SDDS index at 1, leave 0 for others
_SDDS_INDEX = 1
_MAX_SDDS_INDEX = 19
_sdds_lock = threading.RLock()


def extract_sdds_column(filename, field, page_index):
    """ Returns values from one column on one page.
    """
    return process_sdds_page(filename, page_index, _sdds_column, field)


def process_sdds_page(filename, page_index, callback, *args, **kwargs):
    """ Invokes callback on one page of data.
    """
    sdds_index = _next_index()
    try:
        if sdds.sddsdata.InitializeInput(sdds_index, filename) != 1:
            pkdlog('{}: cannot access'.format(filename))
            # In normal execution, the file may not yet be available over NFS
            err = _sdds_error(sdds_index, 'Output file is not yet available.')
        else:
            #TODO(robnagler) SDDS_GotoPage not in sddsdata, why?
            for _ in range(page_index + 1):
                if sdds.sddsdata.ReadPage(sdds_index) <= 0:
                    #TODO(robnagler) is this an error?
                    break
            try:
                kwargs['sdds_index'] = sdds_index
                return callback(*args, **kwargs)
            except SystemError as e:
                pkdlog('{}: page not found in {}'.format(page_index, filename))
                err = _sdds_error(
                    sdds_index,
                    'Output page {} not found'.format(page_index) \
                    if page_index \
                    else 'No output was generated for this report.')
    finally:
        try:
            sdds.sddsdata.Terminate(sdds_index)
        except Exception:
            pass
    return {
        'err': err,
    }


def read_sdds_pages(filename, column_names, group_by_page_number=False):
    """ Returns values from all pages, keyed by column name.
    """
    sdds_index = _next_index()
    res = PKDict()
    try:
        assert sdds.sddsdata.InitializeInput(sdds_index, filename) == 1
        all_names = sdds.sddsdata.GetColumnNames(sdds_index)
        while sdds.sddsdata.ReadPage(sdds_index) > 0:
            for name in column_names:
                if name not in res:
                    res[name] = []
                values = sdds.sddsdata.GetColumn(
                    sdds_index,
                    all_names.index(name),
                )
                if group_by_page_number:
                    values = [values]
                res[name] += values
    finally:
        try:
            sdds.sddsdata.Terminate(sdds_index)
        except Exception:
            pass
    return res


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


def _next_index():
    global _SDDS_INDEX
    with _sdds_lock:
        sdds_index = _SDDS_INDEX
        _SDDS_INDEX += 1
        if _SDDS_INDEX > _MAX_SDDS_INDEX:
            _SDDS_INDEX = 1
    return sdds_index


def _safe_sdds_value(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0
    return v


def _sdds_column(field, sdds_index=0):
    column_names = sdds.sddsdata.GetColumnNames(sdds_index)
    assert field in column_names, 'field not in sdds columns: {}: {}'.format(field, column_names)
    column_def = sdds.sddsdata.GetColumnDefinition(sdds_index, field)
    values = sdds.sddsdata.GetColumn(
        sdds_index,
        column_names.index(field),
    )
    return PKDict(
        values=[_safe_sdds_value(v) for v in values],
        column_names=column_names,
        column_def=column_def,
        err=None,
    )


def _sdds_error(sdds_idx, error_text='invalid data file'):
    sdds.sddsdata.Terminate(sdds_idx)
    return PKDict(
        error=error_text,
    )
