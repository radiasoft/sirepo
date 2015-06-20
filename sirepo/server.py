from pykern import pkio
from subprocess import Popen, PIPE
import flask
import json
import os
import py
import re
import random

app = flask.Flask(__name__, static_folder='package_data/static')

@app.route('/srw')
def srw_root():
    return app.send_static_file('html/srw.html')

@app.route('/srw/run', methods=('GET', 'POST'))
def srw_run():
    print("srw_run()")
    d = _work_dir_name()
    os.makedirs(d)
    with pkio.save_chdir(d):
        pkio.write_text('in.json', flask.request.data.decode('unicode-escape'))

    p = Popen(['python', 'run_srw.py', d], stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    if p.returncode != 0:
        print('run_srw.py failed with status code: {}, dir: {}'.format(p.returncode, d))
        m = re.search('ValueError: ([^\n]+)', err)
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
