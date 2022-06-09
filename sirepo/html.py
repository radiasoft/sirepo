# -*- coding: utf-8 -*-
u"""html template

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import re
import sys


_CALL_RE = re.compile(r'^\s+(\w+)\(([^\)]*)\);', flags=re.MULTILINE)

_ARGS_RE = re.compile(r'\s*,\s*')

_ARG_RE = re.compile(r'^(\w+)=(.*)$', flags=re.DOTALL)

_FUNC_MAP = PKDict()

_FUNC_PREFIX = '_widget_'

def render(path):
    def _dispatch(match):
        f = match.group(1)
        assert f in _FUNC_MAP, \
            f'function={f} not in map path={path}'
        k = PKDict(ctx=PKDict(path=path))
        for a in  _ARGS_RE.split(match.group(2).strip()):
            if not a:
                continue
            m = _ARG_RE.search(a)
            assert m, \
                f'invalid keyword argument={a} function={f} path={path}'
            assert m.group(1) not in k, \
                f'duplicate keyword argument={a} function={f} path={path}'
            k[m.group(1)] = m.group(2)
        return _FUNC_MAP[f](**k)

    return _CALL_RE.sub(_dispatch, pykern.pkio.read_text(path))


def _init():
    import sys, inspect
    for n, o in inspect.getmembers(sys.modules[__name__]):
        if n.startswith(_FUNC_PREFIX) and inspect.isfunction(o):
            _FUNC_MAP[n[len(_FUNC_PREFIX):]] = o


def _widget_sim_settings_and_status(ctx, scope):
    return f'''<div class="col-md-6 col-xl-4">
      <div data-basic-editor-panel="" data-view-name="simulationSettings"></div>
    </div>
    <div class="col-md-6 col-xl-4">
      <div data-simple-panel="simulationStatus">
        <div data-sim-status-panel="{scope}.simState"></div>
      </div>
    </div>
    <div class="clearfix"></div>'''


def _widget_supported_codes(ctx):
    import sirepo.feature_config
    res = '''<li class="supported-codes">
              <button class="dropdown-toggle" type="button" id="sr-landing-supported-codes" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">
                <span>Supported Codes</span>
                <span class="caret"></span>
              </button>
              <ul class="dropdown-menu" aria-labelledby="sr-landing-supported-codes">
    '''
    # TODO(e-carlin): https://git.radiasoft.org/sirepo/issues/3632
    x = PKDict([(sim, sim) for sim in sirepo.feature_config.cfg().sim_types ])
    x.pkupdate(
        activait='ml',
        jupyter='jupyterhublogin',
    )
    new = PKDict(
        xRay=PKDict(name='X-ray Beamlines', desc='Simulate synchrotron radiation and design x-ray beamlines.'),
        particleAccelerators=PKDict(name='Particle Accelerators', desc='Model beam dynamics for a wide range of particle accelerators.'),
        ml=PKDict(name='Machine Learning', desc='Analyze complex datasets and develop machine learning algorithms.'),
        magnets=PKDict(name='Magnets', desc='Build and share 3D simulations of permanent and electromagnets.'),
        vac=PKDict(name='Vacuum Nanoelectronics', desc='Create vacuum nanoelectronics models in your browser.'),
        controls=PKDict(name='Controls', desc='Test automated tuning programs with control-systems codes.'),
        jupyter=PKDict(name='Jupyter', desc='Use our JupyterHub server with resources and libraries built in.'),
        rest=PKDict(name='More Codes', desc='And many more! Check out some of our other codes.')
    )

    for key in x:
        if key in ['srw', 'shadow']:
            new.xRay[key]=x[key]
        elif key in ['elegant', 'opal', 'warppba', 'jspec', 'zgoubi', 'madx', 'synergia']:
            new.particleAccelerators[key] = x[key]
        elif key in ['activait']:
            new.ml[key] = x[key]
        elif key in ['radia']:
            new.magnets[key] = x[key]
        elif key in ['warpvnd']:
            new.vac[key] = x[key]
        elif key in ['controls']:
            new.controls[key] = x[key]
        elif key in ['jupyter']:
            new.jupyter[key] = x[key]
        else:
            new.rest[key]=x[key]



    del x['ml']
    r = ''
    pkdp('\n\n\n x: {}', x)
    pkdp('\n\n\n new: {}', new)

    t = '<div style="display:flex; flex-wrap: wrap; margin: 1em; z-index: 10000;"  class="row">'
    for k in new.keys():
        t += f'''<div style="margin: 1em;" class="item">
                    <img style="max-width: 250px; min-height: 200px;" src="./img/{k}.gif" />
                    <h4> {new[k].name} </h4>
                    <div style="max-width: 250px;"> {new[k].desc} </div>

                    <div style="position: relative;">
                        <button class="dropdown-toggle btn-link" type="button" id="sr-landing-supported-codes" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">
                            <span>Apps</span>
                        </button>
                        <div  class="dropdown-menu">
            '''

        for j in new[k]:
            if j not in ['name', 'desc']:
                t += f'''

                    <p class="text-center">
                        <a href="/{new[k][j]}" style="width: 300px;" class="btn-link"><span>{j.upper()}</span></a>
                    </p>
                    '''
        t += '</div>'
        t += '</div>'
        t += '</div>'


    t += '</div>'
    return t



_init()
