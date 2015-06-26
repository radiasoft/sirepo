from pykern import pkio
from subprocess import Popen, PIPE
import datetime
import flask
import json
import json
import os
import py
import random
import re
import uuid
import sirepo.srw_template

_SIMULATION_DIR = 'simulations/'
_STATIC_FOLDER = 'package_data/static'

app = flask.Flask(__name__, static_folder=_STATIC_FOLDER)

def _simulation_name(res, path, data, params):
    res.append(data['models']['simulation']['name'])

@app.route('/srw/copy-simulation', methods=('GET', 'POST'))
def srw_copy_simulation():
    """Takes the specified simulation and returns a newly named copy with the suffix (copy X)"""
    data = _open_json_file(_simulation_filename_from_id(_json_input('simulationId')))
    base_name = data['models']['simulation']['name']
    names = _iterate_simulation_datafiles(_simulation_name)
    count = 0
    while True:
        count += 1
        name = base_name + ' (copy{})'.format(' {}'.format(count) if count > 1 else '')
        if name in names and count < 100:
            continue
        break
    data['models']['simulation']['name'] = name
    return _save_new_simulation(data)

@app.route('/srw/delete-simulation', methods=('GET', 'POST'))
def srw_delete_simulation():
    #TODO(pjm): ensure it is a proper uuid and corresponds to a simulation json file
    os.remove(_simulation_filename_from_id(_json_input('simulationId')))
    return '{}'

@app.route('/srw/new-simulation', methods=('GET', 'POST'))
def srw_new_simulation():
    data = _open_json_file(os.path.join(_STATIC_FOLDER, 'json/default.json'))
    data['models']['simulation']['name'] = _json_input('name')
    return _save_new_simulation(data)

@app.route('/srw/python-source/<simulation_id>')
def srw_python_source(simulation_id):
    data = _open_json_file(_simulation_filename_from_id(simulation_id))
    # ensure the whole source gets generated, not up to the last breakout report
    if 'report' in data:
        del data['report']
    return flask.Response(
        "{}{}".format(_generate_parameters_file(data), sirepo.srw_template.run_all_text()),
        mimetype="text/plain",
    )

@app.route('/srw')
def srw_root():
    return app.send_static_file('html/srw.html')

@app.route('/srw/run', methods=('GET', 'POST'))
def srw_run():
    print("srw_run()")
    dir = _work_dir_name()
    os.makedirs(dir)
    http_text = _read_http_input()
    data = json.loads(http_text)
    _save_simulation_json(data)

    with pkio.save_chdir(dir):
        pkio.write_text('in.json', http_text)
        pkio.write_text('srw_parameters.py', _generate_parameters_file(data))

        #TODO(pjm): need a kill timer for long calculates, ex. Intensity Report with ebeam horizontal position of 0.05
        p = Popen(['python', '../run_srw.py'], stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        if p.returncode != 0:
            print('run_srw.py failed with status code: {}, dir: {}, error: {}'.format(p.returncode, dir, err))
            m = re.search('Error: ([^\n]+)', err)
            if m:
                error_text = m.group(1)
            else:
                error_text = 'an error occurred'
            return json.dumps({
                'error': error_text,
            })

    with open(os.path.join(dir, 'out.json')) as f:
        data = f.read()
    py.path.local(dir).remove(ignore_errors=True)
    return data

@app.route('/srw/simulation/<simulation_id>')
def srw_simulation_data(simulation_id):
    res = _iterate_simulation_datafiles(_find_simulation_data, {'simulationId': simulation_id})
    if len(res):
        if len(res) > 1:
            print('multiple data files found for id: {}'.format(simulation_id))
        return json.dumps(res[0])
    flask.abort(404)

@app.route('/srw/simulation-list')
def srw_simulation_list():
    return json.dumps(
        sorted(
            _iterate_simulation_datafiles(_process_simulation_list),
            key=lambda row: row['last_modified'],
            reverse=True
        )
    )

_SCALE_VALUES = [
    'period',
    'horizontalPosition',
    'verticalPosition',
    'horizontalApertureSize',
    'verticalApertureSize',
    'horizontalRange',
    'verticalRange',
]

def _escape_and_scale_value(k, v):
    v = str(v).replace("'", '')
    if k in _SCALE_VALUES:
        v = float(v) / 1000;
    return v

def _find_simulation_data(res, path, data, params):
    if str(data['models']['simulation']['simulationId']) == params['simulationId']:
        res.append(data)

def _flatten_data(d, res, prefix=''):
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            _flatten_data(v, res, prefix + k + '_')
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = _escape_and_scale_value(k, v)
    return res

def _generate_parameters_file(data):
    if 'report' in data and re.search('watchpointReport', data['report']):
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][data['report']]
    v = _flatten_data(data['models'], {})
    beamline = data['models']['beamline']
    last_id = None
    if 'report' in data:
        m = re.search('watchpointReport(\d+)', data['report'])
        if m:
            last_id = int(m.group(1))
    v['beamlineOptics'] = sirepo.srw_template.generate_beamline_optics(data['models'], last_id)
    v['beamlineFirstElementPosition'] = beamline[0]['position'] if len(beamline) else 20
    # initial drift = 1/2 undulator length + 2 periods
    v['electronBeamInitialDrift'] = -0.5 * float(data['models']['undulator']['length']) - 2 * float(data['models']['undulator']['period']) / 1000 + float(data['models']['undulator']['longitudinalPosition'])
    return sirepo.srw_template.TEMPLATE.format(**v).decode('unicode-escape')

def _iterate_simulation_datafiles(op, params=None):
    res = []
    for filename in os.listdir(_SIMULATION_DIR):
        if not re.search('\.json$', filename):
            continue
        path = os.path.join(_SIMULATION_DIR, filename)
        if not os.path.isfile(path):
            continue
        try:
            op(res, path, _open_json_file(path), params)
        except ValueError:
            print('unparseable json file: {}'.format(path))

    return res

def _json_input(field):
    return json.loads(_read_http_input())[field]

def _open_json_file(path):
    with open(path) as f:
        return json.load(f)

def _process_simulation_list(res, path, data, params):
    res.append({
        'simulationId': data['models']['simulation']['simulationId'],
        'name': data['models']['simulation']['name'],
        'last_modified': datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M'),
    })

def _read_http_input():
    return flask.request.data.decode('unicode-escape')

def _save_new_simulation(data):
    #TODO(pjm): use database sequence for Id
    id = str(uuid.uuid1())
    data['models']['simulation']['simulationId'] = id
    _save_simulation_json(data)
    return srw_simulation_data(id)

def _save_simulation_json(data):
    id = data['models']['simulation']['simulationId']
    with open(_simulation_filename_from_id(id), 'w') as outfile:
        json.dump(data, outfile)

def _simulation_filename_from_id(id):
    return os.path.join(_SIMULATION_DIR, id) + '.json'

def _work_dir_name():
    d = 'work{}'.format(random.random())
    tries = 0
    while os.path.exists(d):
        if tries > 3:
            raise Exception('failed to create unique directory name')
        d = 'work{}'.format(random.random())
        tries += 1
    return d


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=1)
