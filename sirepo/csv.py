"""wrappers to Python csv

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import csv
import re

_ENCODINGS = ("cp1252", "utf-8", "utf-8-sig")


def open_csv(path, encoding="utf-8"):
    with open(str(path), "rt", encoding=encoding) as f:
        for r in csv.reader(f):
            yield r


def read_as_number_list(path):
    try:
        return read_as_list(path, data_type=float)
    except ValueError as e:
        raise RuntimeError(f'invalid file "{path.basename}" err={e}')


def read_as_list(path, data_type=str):
    for e in _ENCODINGS:
        skip_header = data_type != str
        try:
            res = []
            for r in open_csv(path, encoding=e):
                if skip_header and len(r) and re.search(r"[A-Za-z]", r[0]):
                    skip_header = False
                    continue
                res.append([data_type(c) for c in r])
            return res
        except (TypeError, UnicodeDecodeError, ValueError):
            pkdlog("file={} cannot be read with encoding {}", path.basename, e)
    raise RuntimeError(f'invalid file "{path.basename}"')
