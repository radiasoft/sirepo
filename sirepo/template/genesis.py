# -*- coding: utf-8 -*-
u"""Genesis execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import numpy as np
import re
import sirepo.job
import sirepo.sim_data
import sirepo.simulation_db


# http://genesis.web.psi.ch/Manual/parameter.html
# In the docs the param is ITGAMGAUS. The code expect IGAMGAUS

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


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

_OUTPUT_FILENAME = 'genesis.out'
_FIELD_DISTRIBUTION_OUTPUT_FILENAME = _OUTPUT_FILENAME + '.fld'
_PARTICLE_OUTPUT_FILENAME = _OUTPUT_FILENAME + '.par'

_RUN_ERROR_RE = re.compile(r'(?:^\*\*\* )(.*error.*$)', flags=re.MULTILINE)

# POSIT: Same order as results in _OUTPUT_FILENAME
_SLICE_COLS = (
    'z [m]',
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
    c = _get_frame_counts(run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1,
        particleFrameCount=c.particle,
        fieldFrameCount=c.field,
    )


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    if model == 'particleAnimation':
        return _PARTICLE_OUTPUT_FILENAME
    if model == 'fieldDistributionAnimation':
        return _FIELD_DISTRIBUTION_OUTPUT_FILENAME
    if model == 'parameterAnimation':
        return _OUTPUT_FILENAME
    raise AssertionError('unknown model={}'.format(model))


def import_file(req, **kwargs):
    text = pkcompat.from_bytes(req.file_stream.read())
    if not bool(re.search(r'\.in$', req.filename, re.IGNORECASE)):
        raise AssertionError('invalid file extension, expecting .in')
    res = sirepo.simulation_db.default_data(SIM_TYPE)
    p = pkio.py_path(req.filename)
    res.models.simulation.name = p.purebasename
    return _parse_namelist(res, text)


def post_execution_processing(run_dir=None, **kwargs):
    if _genesis_success_exit(run_dir):
        return
    return _parse_genesis_error(run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def sim_frame_fieldDistributionAnimation(frame_args):
    r = _get_field_distribution(frame_args.sim_in)
    d = np.abs(r[int(frame_args.frameIndex), 0, :, :])
    s = d.shape[0]
    return PKDict(
        title=_z_title_at_frame(frame_args, frame_args.sim_in.models.io.ipradi),
        x_label='',
        x_range=[0, s, s],
        y_label='',
        y_range=[0, s, s],
        z_matrix=d.tolist(),
    )


def sim_frame_parameterAnimation(frame_args):
    l, s = _get_lattice_and_slice_data(frame_args.run_dir)
    x = _SLICE_COLS[0]
    plots = []
    for f in ('y1', 'y2', 'y3'):
        y = frame_args[f]
        if not y or y == 'none':
            continue
        plots.append(
            PKDict(
                field=y,
                points=l[:, _LATTICE_COLS.index(y)].tolist(),
                label=y,
            )
        )
    return template_common.parameter_plot(
        s[:, _SLICE_COLS.index(x)].tolist(),
        plots,
        PKDict(),
        PKDict(
            title='',
            x_label=x,
        )
    )


def sim_frame_particleAnimation(frame_args):
    def _get_col(col_key):
        # POSIT: ParticleColumn keys are in same order as columns in output
        for i, c in enumerate(SCHEMA.enum.ParticleColumn):
            if c[0] == col_key:
              return i, c[1]
        raise AssertionError(
            f'No column={SCHEMA.enum.ParticleColumn} with key={col_key}',
        )
    n = frame_args.sim_in.models.electronBeam.npart
    d = np.fromfile(_PARTICLE_OUTPUT_FILENAME , dtype=np.float64)
    b = d.reshape(
        int(len(d) / len(SCHEMA.enum.ParticleColumn) / n),
        len(SCHEMA.enum.ParticleColumn),
        n,
    )
    x = _get_col(frame_args.x)
    y = _get_col(frame_args.y)
    return template_common.heatmap(
        [
            b[int(frame_args.frameIndex), x[0], :].tolist(),
            b[int(frame_args.frameIndex), y[0], :].tolist(),
        ],
        frame_args.sim_in.models.particleAnimation.pkupdate(frame_args),
        PKDict(
            title=_z_title_at_frame(frame_args, frame_args.sim_in.models.io.ippart),
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
    # TODO(pjm): only support time independent simulations for now
    data.models.timeDependence.itdp = 0
    io = data.models.io
    io.outputfile = _OUTPUT_FILENAME
    io.iphsty = 1
    io.ishsty = 1
    r= ''
    fmap = PKDict(
        wcoefz1='WCOEFZ(1)',
        wcoefz2='WCOEFZ(2)',
        wcoefz3='WCOEFZ(3)',
    )
    for m in _INPUT_VARIABLE_MODELS:
        for f, v in data.models[m].items():
            if f not in SCHEMA.model[m]:
                continue
            s = SCHEMA.model[m][f]
            if v == s[2] or str(v) == s[2]:
                continue
            if s[1] == 'String':
                v = f"'{v}'"
            elif s[1] == 'InputFile':
                if v:
                    v = f"'{_SIM_DATA.lib_file_name_with_model_field('io', f, v)}'"
                else:
                    continue
            r += f'{fmap.get(f, f.upper())} = {v}\n'
    if data.models.io.maginfile:
        r += 'MAGIN = 1\n'
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(input_filename=_INPUT_FILENAME, variables=r),
    )


def _genesis_success_exit(run_dir):
    # Genesis exits with a 0 status regardless of whether it succeeded or failed
    # Assume success if _OUTPUT_FILENAME exists
    return run_dir.join(_OUTPUT_FILENAME).exists()


def _get_field_distribution(data):
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


def _get_frame_counts(run_dir):
    res = PKDict(
        particle=0,
        field=0,
    )
    with pkio.open_text(run_dir.join(_OUTPUT_FILENAME)) as f:
        for line in f:
            m = re.match('^\s*(\d+) (\w+): records in z', line)
            if m:
                res[m.group(2)] = int(m.group(1))
                if m.group(1) == 'field':
                    break
    return res



def _parse_genesis_error(run_dir):
    return '\n'.join(
        [
            m.group(1).strip() for m in
            _RUN_ERROR_RE.finditer(pkio.read_text(run_dir.join(template_common.RUN_LOG)))
        ],
    )

def _parse_namelist(data, text):
    dm = data.models
    nls = template_common.NamelistParser().parse_text(text)
    if 'newrun' not in nls:
        raise AssertionError('Missing "newrun" namelist')
    nl = nls['newrun']

    if 'wcoefz' in nl:
        nl['wcoefz1'] = nl['wcoefz'][0]
        nl['wcoefz2'] = nl['wcoefz'][1]
        nl['wcoefz3'] = nl['wcoefz'][2]

    for m in SCHEMA.model:
        for f in SCHEMA.model[m]:
            if f not in nl:
                continue
            v = nl[f]
            if isinstance(v, list):
                v = v[-1]
            t = SCHEMA.model[m][f][1]
            d = dm[m]
            if t == 'Float':
                d[f] = float(v)
            elif t == 'Integer':
                d[f] = int(v)
            elif t == 'Boolean':
                d[f] = '1' if int(v) else '0'
            elif t == 'ItGaus':
                d[f] = '1' if int(v) == 1 else '2' if int(v) == 2 else '3'
            elif t == 'Lbc':
                d[f] = '0' if int(v) == 0 else '1'
            elif t == 'Iertyp':
                v = int(v)
                if v < -2 or v > 2:
                    v = 0
                d[f] = str(v)
            elif t == 'Iwityp':
                d[f] = '0' if int(v) == 0 else '1'
            elif t == 'TaperModel':
                d[f] = '1' if int(v) == 1 else '2' if int(v) == 2 else '0'
    #TODO(pjm): remove this if scanning or time dependence is implemented in the UI
    dm.scan.iscan = '0'
    dm.timeDependence.itdp = '0'
    return data


def _z_title_at_frame(frame_args, nth):
    _, s = _get_lattice_and_slice_data(frame_args.run_dir)
    step = frame_args.frameIndex * nth
    z = s[:, 0][step]
    return f'z: {z:.6f} [m] step: {step + 1}'
