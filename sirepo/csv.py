from pykern.pkdebug import pkdc, pkdp, pkdlog
import csv

_ENCODINGS = ("cp1252", )


def open_csv(path, encoding="utf-8"):
    with open(str(path), "rt", encoding=encoding) as f:
        for r in csv.reader(f):
            yield r


def read_as_number_array(path):
    res = []
    for e in _ENCODINGS:
        try:
            for r in open_csv(path, encoding=e):
                res.append([float(c.strip()) for c in r])
            return res
        except (TypeError, UnicodeDecodeError, ValueError):
            pkdlog("file={} cannot be read with encoding {}", path.basename, e)
    raise RuntimeError("invalid file={}".format(path.basename))
