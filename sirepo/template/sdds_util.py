# -*- coding: utf-8 -*-
u"""SDDS utilities.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import math
import sdds

_SDDS_INDEX = 0


def extract_sdds_column(filename, field, page_index):
    try:
        if sdds.sddsdata.InitializeInput(_SDDS_INDEX, filename) != 1:
            pkdlog('{}: cannot access'.format(filename))
            # In normal execution, the file may not yet be available for NFS
            err = _sdds_error('Output file is not yet available.')
        else:
            column_names = sdds.sddsdata.GetColumnNames(_SDDS_INDEX)
            #TODO(robnagler) SDDS_GotoPage not in sddsdata, why?
            for _ in xrange(page_index + 1):
                if sdds.sddsdata.ReadPage(_SDDS_INDEX) <= 0:
                    #TODO(robnagler) is this an error?
                    break
            try:
                column_def = sdds.sddsdata.GetColumnDefinition(_SDDS_INDEX, field)
                values = sdds.sddsdata.GetColumn(
                    _SDDS_INDEX,
                    column_names.index(field),
                )
                return (
                    map(lambda v: _safe_sdds_value(v), values),
                    column_names,
                    column_def,
                    None,
                )
            except SystemError as e:
                pkdlog('{}: page not found in {}'.format(page_index, filename))
                err = _sdds_error('Output page {} not found'.format(page_index) if page_index else 'No output was generated for this report.')
    finally:
        try:
            sdds.sddsdata.Terminate(_SDDS_INDEX)
        except Exception:
            pass
    return None, None, None, err


def _safe_sdds_value(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0
    return v


def _sdds_error(error_text='invalid data file'):
    sdds.sddsdata.Terminate(_SDDS_INDEX)
    return {
        'error': error_text,
    }
