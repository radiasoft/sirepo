import flask
app = flask.Flask(__name__, static_folder='package_data/static')

@app.route('/srw')
def srw_root():
    return app.send_static_file('html/srw.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=1)
