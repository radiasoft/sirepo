# -*- coding: utf-8 -*-
u"""OPAL execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import lattice
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import h5py
import numpy as np
import re
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

WANT_BROWSER_FRAME_CACHE = True

_DIM_INDEX = PKDict(
    x=0,
    y=1,
    z=2,
)
_OPAL_H5_FILE = 'opal.h5'
_OPAL_INPUT_FILE = 'opal.in'


class OpalElementIterator(lattice.ElementIterator):
    def is_ignore_field(self, field):
        # TODO(pjm): remove fmapfn when implemented
        return field in ['name', 'fmapfn']


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        #TODO(pjm): determine total frame count and set percentComplete
        res.frameCount = _read_frame_count(run_dir) - 1
        return res
    if run_dir.join('{}.json'.format(template_common.INPUT_BASE_NAME)).exists():
        res.frameCount = _read_frame_count(run_dir)
        if res.frameCount > 0:
            res.percentComplete = 100
    return res


def get_application_data(data):
    if data.method == 'compute_particle_ranges':
        return template_common.compute_field_range(data, _compute_range_across_frames)
    assert False, 'unknown get_application_data: {}'.format(data)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(_OPAL_INPUT_FILE),
        _generate_parameters_file(data),
    )


def _compute_range_across_frames(run_dir, data):
    def _walk_file(h5file, key, step, res):
        if key:
            for field in res:
                v = np.array(h5file['/{}/{}'.format(key, field)])
                min1, max1 = v.min(), v.max()
                if res[field]:
                    if res[field][0] > min1:
                        res[field][0] = min1
                    if res[field][1] < max1:
                        res[field][1] = max1
                else:
                    res[field] = [min1, max1]
    res = PKDict()
    for v in _SCHEMA.enum.PhaseSpaceCoordinate:
        res[v[0]] = None
    return _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, res)


def sim_frame_bunchAnimation(frame_args):
    a = frame_args.sim_in.models.bunchAnimation
    a.update(frame_args)
    res = PKDict()
    with h5py.File(str(a.run_dir.join(_OPAL_H5_FILE)), 'r') as f:
        for field in ('x', 'y'):
            res[field] = PKDict(
                name=a[field],
                points=np.array(f['/Step#{}/{}'.format(a.frameIndex, a[field])]),
            )
            _units_from_hdf5(f, res[field])
    return template_common.heatmap([res.x.points, res.y.points], a, PKDict(
        x_label=res.x.label,
        y_label=res.y.label,
    ))


def sim_frame_plotAnimation(frame_args):

    def _walk_file(h5file, key, step, res):
        if key:
            for field in res.values():
                field.points.append(h5file[key].attrs[field.name][field.index])
        else:
            for field in res.values():
                _units_from_hdf5(h5file, field)

    res = PKDict()
    for dim in 'x', 'y1', 'y2', 'y3':
        parts = frame_args[dim].split(' ')
        if parts[0] == 'none':
            continue
        res[dim] = PKDict(
            dim=dim,
            points=[],
            name=parts[0],
            index=_DIM_INDEX[parts[1]] if len(parts) > 1 else 0,
        )
    _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, res)
    plots = []
    for field in res.values():
        if field.dim != 'x':
            plots.append(PKDict(
                label=field.label,
                points=field.points,
            ))
    return template_common.parameter_plot(
        res.x.points,
        plots,
        PKDict(),
        PKDict(
            title='',
            y_label='',
            x_label=res.x.label,
        ),
    )


def _format_field_value(state, model, field, el_type):
    value = model[field]
    if el_type == 'Boolean':
        value = 'true' if value == '1' else 'false'
    #TODO(pjm): determine the general case where values need quotes
    if LatticeUtil.is_command(model) and model._type == 'run' and field == 'method':
        value = '"{}"'.format(value)
    return [field, value]


def _generate_commands(util):
    return util.render_lattice(
        util.iterate_models(
            OpalElementIterator(None, _format_field_value),
            'commands',
        ).result,
        want_semicolon=True)


def _generate_lattice(util):
    res = util.render_lattice(
        util.iterate_models(
            OpalElementIterator(None, _format_field_value),
            'elements',
        ).result,
        want_semicolon=True) + '\n'
    beamline_id = util.select_beamline().id
    count_by_name = PKDict()
    names = []
    res += _generate_beamline(util, count_by_name, beamline_id, 0, names)[0]
    res += '{}: LINE=({});\n'.format(
        util.id_map[beamline_id].name,
        ','.join(names),
    )
    return res


def _generate_beamline(util, count_by_name, beamline_id, edge, names):
    res = ''
    for item_id in util.id_map[beamline_id]['items']:
        item = util.id_map[item_id]
        if 'type' in item:
            # element
            name = item.name
            if name not in count_by_name:
                count_by_name[name] = 0
            name = '"{}#{}"'.format(name, count_by_name[name])
            names.append(name)
            count_by_name[item.name] += 1
            res += '{}: {},elemedge={};\n'.format(name, item.name, edge)
            edge += item.l
        else:
            # beamline
            text, edge = _generate_beamline(util, count_by_name, item_id, edge, names)
            res += text
    return res, edge


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = LatticeUtil(data, _SCHEMA)
    v.update(dict(
        lattice=_generate_lattice(util),
        use_beamline=util.select_beamline().name,
        commands=_generate_commands(util),
    ))
    report = data.get('report', '')
    if report == 'twissReport':
        return template_common.render_jinja(SIM_TYPE, v, 'twiss.in')
    return template_common.render_jinja(SIM_TYPE, v, 'parameters.in')


def _iterate_hdf5_steps(path, callback, state):
    with h5py.File(str(path), 'r') as f:
        step = 0
        key = 'Step#{}'.format(step)
        while key in f:
            callback(f, key, step, state)
            step += 1
            key = 'Step#{}'.format(step)
        callback(f, None, -1, state)
    return state


def _read_frame_count(run_dir):
    def _walk_file(h5file, key, step, res):
        if key:
            res[0] = step + 1
    try:
        return _iterate_hdf5_steps(run_dir.join(_OPAL_H5_FILE), _walk_file, [0])[0]
    except IOError:
        pass
    return 0


def _units_from_hdf5(h5file, field):
    units = h5file.attrs['{}Unit'.format(field.name)]
    if units == '1':
        units = ''
    elif units[0] == 'M' and len(units) > 1:
        units = re.sub(r'^.', '', units)
        field.points = (np.array(field.points) * 1e6).tolist()
    elif units[0] == 'G' and len(units) > 1:
        units = re.sub(r'^.', '', units)
        field.points = (np.array(field.points) * 1e9).tolist()
    field.label = field.name
    if units:
        if re.search(r'^#', units):
            field.label += ' ({})'.format(units)
        else:
            field.label += ' [{}]'.format(units)
    field.units = units
