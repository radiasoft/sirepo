import csv
import io
import pytest
import re
import time
from pykern.pkcollections import PKDict
from pykern.pkunit import pkeq
import sirepo.resource
from pykern.pkdebug import pkdp


def test_favicon(fc):
    r = fc.sr_get("favicon")
    pkdp(f"r.data={r.data}")
