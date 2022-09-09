# -*- coding: utf-8 -*-
"""html template

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import re
import sys


_CALL_RE = re.compile(r"^\s+(\w+)\(([^\)]*)\);", flags=re.MULTILINE)

_ARGS_RE = re.compile(r"\s*,\s*")

_ARG_RE = re.compile(r"^(\w+)=(.*)$", flags=re.DOTALL)

_FUNC_MAP = PKDict()

_FUNC_PREFIX = "_widget_"


def render(path):
    def _dispatch(match):
        f = match.group(1)
        assert f in _FUNC_MAP, f"function={f} not in map path={path}"
        k = PKDict(ctx=PKDict(path=path))
        for a in _ARGS_RE.split(match.group(2).strip()):
            if not a:
                continue
            m = _ARG_RE.search(a)
            assert m, f"invalid keyword argument={a} function={f} path={path}"
            assert (
                m.group(1) not in k
            ), f"duplicate keyword argument={a} function={f} path={path}"
            k[m.group(1)] = m.group(2)
        return _FUNC_MAP[f](**k)

    return _CALL_RE.sub(_dispatch, pykern.pkio.read_text(path))


def _init():
    import sys, inspect

    for n, o in inspect.getmembers(sys.modules[__name__]):
        if n.startswith(_FUNC_PREFIX) and inspect.isfunction(o):
            _FUNC_MAP[n[len(_FUNC_PREFIX) :]] = o


def _widget_sim_settings_and_status(ctx, scope):
    return f"""<div class="col-md-6 col-xl-4">
      <div data-basic-editor-panel="" data-view-name="simulationSettings"></div>
    </div>
    <div class="col-md-6 col-xl-4">
      <div data-simple-panel="simulationStatus">
        <div data-sim-status-panel="{scope}.simState"></div>
      </div>
    </div>
    <div class="clearfix"></div>"""


def _widget_supported_codes(ctx):
    import sirepo.feature_config

    res = """<li class="supported-codes">
              <button class="dropdown-toggle" type="button" id="sr-landing-supported-codes" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">
                <span>Supported Codes</span>
                <span class="caret"></span>
              </button>
              <ul class="dropdown-menu" aria-labelledby="sr-landing-supported-codes">
    """
    # TODO(e-carlin): https://git.radiasoft.org/sirepo/issues/3632
    x = PKDict([(s, s) for s in sirepo.feature_config.cfg().sim_types])
    x.pkupdate(
        jupyter="jupyterhublogin",
    )
    r = """
        <div class="container">
          <div class="row">
    """
    for k in sorted(x.keys()):
        r += f"""
              <div class="col-xl-3 col-lg-4 col-sm-6 ">
                <p style="margin: 1em;" class="text-center">
                  <a href="/{x[k]}" style="width: 250px;" class="btn-link"><span>{k.upper()}</span></a>
                </p>
              </div>
        """
    r += """
          </div>
        </div>
        """
    return r


_init()
