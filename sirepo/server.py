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

_SIMULATION_DIR = 'simulations/'
_STATIC_FOLDER = 'package_data/static'

app = flask.Flask(__name__, static_folder=_STATIC_FOLDER)

@app.route('/srw/copy-simulation', methods=('GET', 'POST'))
def srw_copy_simulation():
    id = json.loads(_read_http_input())['simulationId']
    source_file = _simulation_filename_from_id(id)
    with open(source_file) as f:
        data = json.load(f)
    data['models']['simulation']['name'] += ' (copy)'
    return _save_new_simulation(data)

@app.route('/srw/delete-simulation', methods=('GET', 'POST'))
def srw_delete_simulation():
    id = json.loads(_read_http_input())['simulationId']
    #TODO(pjm): ensure it is a proper uuid and corresponds to a simulation json file
    os.remove(_simulation_filename_from_id(id))
    return '{}'

@app.route('/srw/new-simulation', methods=('GET', 'POST'))
def srw_new_simulation():
    with open(os.path.join(_STATIC_FOLDER, 'json/default.json')) as f:
        data = json.load(f)
    data['models']['simulation']['name'] = json.loads(_read_http_input())['name']
    return _save_new_simulation(data)

@app.route('/srw')
def srw_root():
    return app.send_static_file('html/srw.html')

@app.route('/srw/run', methods=('GET', 'POST'))
def srw_run():
    print("srw_run()")
    d = _work_dir_name()
    os.makedirs(d)
    http_text = _read_http_input()
    _save_simulation_json(json.loads(http_text))

    with pkio.save_chdir(d):
        pkio.write_text('in.json', http_text)

    #TODO(pjm): need a kill timer for long calculates, ex. Intensity Report with ebeam horizontal position of 0.05
    p = Popen(['python', 'run_srw.py', d], stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    if p.returncode != 0:
        print('run_srw.py failed with status code: {}, dir: {}, error: {}'.format(p.returncode, d, err))
        m = re.search('Error: ([^\n]+)', err)
        if m:
            error_text = m.group(1)
        else:
            error_text = 'an error occurred'
        return json.dumps({
            'error': error_text,
        })

    with open(os.path.join(d, 'out.json')) as f:
        data = f.read()
    py.path.local(d).remove(ignore_errors=True)
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

def _find_simulation_data(res, path, data, params):
    if str(data['models']['simulation']['simulationId']) == params['simulationId']:
        res.append(data)

def _iterate_simulation_datafiles(op, params=None):
    res = []
    for filename in os.listdir(_SIMULATION_DIR):
        if not re.search('\.json$', filename):
            continue
        path = os.path.join(_SIMULATION_DIR, filename)
        if not os.path.isfile(path):
            continue
        with open(path) as f:
            data = json.load(f)
        op(res, path, data, params)
    return res

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
