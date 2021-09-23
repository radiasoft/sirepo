# -*- coding: utf-8 -*-
u"""Genesis execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import numpy as np
import re
import sirepo.job
import sirepo.sim_data
import sirepo.simulation_db


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()


_INPUT_VARIABLE_MODELS = (
    'electronBeam',
    'focusing',
    'io',
    'particleLoading',
    'mesh',
    'radiation',
    'scan',
    'simulationControl' ,
    'timeDependence',
    'undulator'
)

_INPUT_FILENAME = 'genesis.in'

# POSIT: Same order as results in _OUTPUT_FILENAME
_LATTICE_COLS = (
    'power',
    'increment',
    'p_mid',
    'phi_mid',
    'r_size',
    'energy',
    'bunching',
    'xrms',
    'yrms',
    'error',
)

_LATTICE_DATA_FILENAME = 'lattice.npy'

_LATTICE_RE = re.compile(r'^.+power[\s\w]+\n(.*)', flags=re.DOTALL)

# POSIT: Same name as outputfile in schema
_OUTPUT_FILENAME = 'genesis.out'
_FIELD_DISTRIBUTION_OUTPUT_FILENAME = _OUTPUT_FILENAME + '.fld'
_PARTICLE_OUTPUT_FILENAME = _OUTPUT_FILENAME + '.par'

_RUN_ERROR_RE = re.compile(r'(?:^\*\*\* )(.*error.*$)', flags=re.MULTILINE)

# POSIT: Same order as results in _OUTPUT_FILENAME
_SLICE_COLS = (
    'z[m]',
    'aw',
    'qfld',
)

_SLICE_DATA_FILENAME = 'slice.npy'

_SLICE_RE = re.compile(
    r'\s+z\[m\]\s+aw\s+qfld\s+\n(.*)\n^\s*$\n\*',
    flags=re.DOTALL|re.MULTILINE,
)

def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(percentComplete=0, frameCount=0)
    if not _genesis_success_exit(run_dir):
        return PKDict(
            percentComplete=100,
            state=sirepo.job.ERROR,
        )
    return PKDict(
        percentComplete=100,
        frameCount=_get_field_distribution(
            sirepo.simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME),
            ),
        ).shape[0],
    )


def post_execution_processing(run_dir=None, **kwargs):
    if _genesis_success_exit(run_dir):
        return
    return _parse_genesis_error(run_dir)


def sim_frame_fieldDistributionAnimation(frame_args):
    r = _get_field_distribution(frame_args.sim_in)
    d = np.abs(r[int(frame_args.frameIndex), 0, :, :])
    s = d.shape[0]
    return PKDict(
        title='Field Distribution',
        x_label='',
        x_range=[0, s, s],
        y_label='',
        y_range=[0, s, s],
        z_matrix=d.tolist(),
    )


def sim_frame_parameterAnimation(frame_args):
    l, s = _get_lattice_and_slice_data(frame_args.run_dir)
    x = 'z[m]'
    y = frame_args.y
    return template_common.parameter_plot(
        s[:, _SLICE_COLS.index(x)].tolist(),
        [PKDict(
            field=y,
            points=l[:, _LATTICE_COLS.index(y)].tolist(),
            label=y,
        )],
        PKDict(),
        PKDict(
            title=f'Slice',
            x_label=x,
            y_label=y,
        )
    )


def sim_frame_particleAnimation(frame_args):
    def _get_col(col_key):
        # POSIT: ParticleColumn keys are in same order as columns in output
        for i, c in enumerate(_SCHEMA.enum.ParticleColumn):
            if c[0] == col_key:
              return i, c[1]
        raise AssertionError(
            f'No column={_SCHEMA.enum.ParticleColumn} with key={col_key}',
        )
    n = frame_args.sim_in.models.electronBeam.npart
    d = np.fromfile(_PARTICLE_OUTPUT_FILENAME , dtype=np.float64)
    b = d.reshape(
        int(len(d) / len(_SCHEMA.enum.ParticleColumn) / n),
        len(_SCHEMA.enum.ParticleColumn),
        n,
    )
    x = _get_col(frame_args.x)
    y = _get_col(frame_args.y)
    return template_common.heatmap(
        [
            b[-1, x[0], :].tolist(),
            b[-1, y[0], :].tolist(),
        ],
        frame_args.sim_in.models.particleAnimation.pkupdate(frame_args),
        PKDict(
            title=f'Particles',
            x_label=x[1],
            y_label=y[1],
        ),
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    """
    http://genesis.web.psi.ch/Manual/parameter.html
    - In the docs the param is ITGAMGAUS. The code expect IGAMGAUS

    Some defaults in genesis-schema.json are not set to the default value defined in the docs.
    - IPPART: Default in schema is 1 because we need the file to do plotting. Docs default is 0.
    - IPPRADI: Default in schema is 1 because we need the file to do plotting. Docs default is 0.
    """
    r= ''
    for m in _INPUT_VARIABLE_MODELS:
        for f, v in data.models[m].items():
            s = _SCHEMA.model[m][f]
            if s[1] == 'String':
                v = f"'{v}'"
            r += f'{s[0]} = {v}\n'
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(input_filename=_INPUT_FILENAME, variables=r),
    )


def _genesis_success_exit(run_dir):
    # Genesis exits with a 0 status regardless of whether it succeeded or failed
    # Assume success if _OUTPUT_FILENAME exists
    return run_dir.join(_OUTPUT_FILENAME).exists()


def _get_field_distribution(data):
    assert data.models.timeDependence.itdp == 0, \
        'Only time independent simulations are currently supported'
    n = 1 # TODO(e-carlin): Will be different for time dependent
    p = data.models.mesh.ncar
    d = np.fromfile(_FIELD_DISTRIBUTION_OUTPUT_FILENAME, dtype=np.float64)
    # Divide by 2 to combine real and imaginary parts which are written separately
    s = int(d.shape[0] / (n * p * p) / 2)
    d = d.reshape(s, n, 2, p, p)
    # recombine as a complex number
    return d[:, :, 0, :, :] + 1.j * d[:, :, 1, :, :]


def _get_lattice_and_slice_data(run_dir):
    def _reshape_and_persist(data, cols, filename):
        d = data.reshape(int(data.size / len(cols)), len(cols))
        np.save(filename, d)
        return d

    f = run_dir.join(_LATTICE_DATA_FILENAME)
    if f.exists():
        return np.load(str(f)), np.load(str(run_dir.join(_SLICE_DATA_FILENAME)))
    o = pkio.read_text(_OUTPUT_FILENAME)
    return (
        _reshape_and_persist(
            np.fromstring(_LATTICE_RE.search(o)[1], sep='\t'),
            _LATTICE_COLS,
            _LATTICE_DATA_FILENAME,
        ),
        _reshape_and_persist(
            np.fromstring(_SLICE_RE.search(o)[1], sep='\t'),
            _SLICE_COLS,
            _SLICE_DATA_FILENAME,
        ),
    )


def _parse_genesis_error(run_dir):
    return '\n'.join(
        [
            m.group(1).strip() for m in
            _RUN_ERROR_RE.finditer(pkio.read_text(run_dir.join(template_common.RUN_LOG)))
        ],
    )
