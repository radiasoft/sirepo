import flask
app = flask.Flask(__name__, static_folder='package_data/static')

@app.route('/srw')
def srw_root():
    return app.send_static_file('html/srw.html')

@app.route('/srw/run', methods=('GET', 'POST'))
def srw_run():
    print("in srw_run()")
    print(flask.request.json)
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=1)
