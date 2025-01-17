from flask import send_from_directory
import os

from flask import Flask, request, redirect, url_for, flash
from google.cloud import storage
import logging
from flask import render_template
from werkzeug.utils import secure_filename
try:
    from io import StringIO # Python 3 from io import StringIO # Python 3
except:
    from StringIO import StringIO
    from io import BytesIO as StringIO

from oauth2client.client import GoogleCredentials
from googleapiclient import discovery
from googleapiclient import errors
from io import StringIO
import csv
import json
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
import pymsgbox

app = Flask(__name__)
app.secret_key = '1234'

# build a service obj
ml = discovery.build('ml', 'v1')
service = build('ml', 'v1')

# Instantiates a client
client = storage.Client()
# creates bucket
bucket = client.get_bucket('kanalyzers.appspot.com')


# bucket name vars for something sam was doing
PROJECT_NAME = 'kanalyzers'
MODEL_BUCKET = 'kanalyzers.appspot.com'
MODEL_FILENAME = 'tf_model.h5'
MODEL = None


# upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['csv', 'xml'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

output_stream= StringIO()

def csvtojson(filename):
    csvfile = open(UPLOAD_FOLDER+'/'+filename, 'r')
    reader = csv.reader(csvfile)
    next(reader)
    ret = []
    for row in reader:
        cur = []
        for col in row:
            cur.append(int(col))
        ret.append(cur)

    return ret





@app.route('/uploads/<filename>')

def upload(filename):
    # Sending uploaded CSV to our Cloud ML model
    service = discovery.build('ml', 'v1')

    name = 'projects/{}/models/{}'.format('kanalyzers', 'juliakeras')
    instances = csvtojson(filename)

    # values = ', '.join(str(v) for v in instances)
    #
    # return values


    response = service.projects().predict(
        name=name,
        body={"instances": instances }
    ).execute()

    if 'error' in response:
        raise RuntimeError(response['error'])

    send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    #response['predictions'][0]['dense_2'][0] accesses the returned click probabilities

    #looping through returned predictions to get all probilities returned by model
    ret = []
    for p in response['predictions']:
        if p['dense_2'][0] > 0.25:
            p = 1
        else:
            p = 0
        ret.append(p)

    df = pd.read_csv(UPLOAD_FOLDER+'/'+filename)
    df.insert(0, "click", ret )
    #df.to_csv(UPLOAD_FOLDER+"/clickpredictions.csv", index=False)
    df.to_csv("static/data/clickpredictions.csv", index=False)

    filename = str(filename)
    flash("Predictions Succesfully Retrieved!", "upload")
    flash("From file " + filename, "fromfile")
    # flash(" + filename + ", "fromfile")

    # values = ', '.join(str(v) for v in ret)
    #
    # return values

    return redirect(url_for('dashboard'))
    return render_template('dashboard.html')




@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        # if file.filename == '':
        #     flash('No selected file')
        #     return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload', filename=filename))
            # return redirect(url_for('dashboard'))
            # return upload(filename)

    return render_template('dashboard.html')

@app.route('/uploads')
def uploads():
    pass

@app.route('/dataviz.html')
def dataviz():
    return render_template('dataviz.html')

@app.route('/dashboard.html')
def dashboard():
    return render_template('dashboard.html')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/form.html')
def form():
    return render_template('form.html')

@app.route('/aboutus.html')
def aboutus():
    return render_template('aboutus.html')

@app.route('/tables.html')
def tables():
    return render_template('tables.html')


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=9000, debug=True)
    #http_server = WSGIServer(('', 5000), app)
    #http_server.serve_forever()
    # [END gae_flex_quickstart]
