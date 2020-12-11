# A remote cotrol app that runs in your browser.
# Shows you live view, allows taking photos, and shows you the post-photo preview.
# Modeled after https://medium.com/datadriveninvestor/video-streaming-using-flask-and-opencv-c464bf8473d6
# and https://blog.miguelgrinberg.com/post/video-streaming-with-flask/page/8

import sys, os
# To import pysony from this repo
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
import pysony

from flask import Flask, Response, render_template, request, send_file
import time
import string
import random
from error_image import get_jpeg_for_message
import requests
from io import BytesIO
import webbrowser

app = Flask(__name__)

# Make a random boundary string
_multipart_boundary = ''.join(random.choices(string.ascii_uppercase + string.digits, k=50))

def sony_error(result):
    if not 'error' in result.keys():
        return None
    msg = f'Camera responded with an error: {result["error"]}.'
    app.logger.error(msg)
    return msg

def get_stream_frame(binary_data):
    return f'--{_multipart_boundary}\r\n'.encode() + \
           b'Content-Type: image/jpeg\r\n\r\n' + binary_data + b'\r\n\r\n'

camera = None
live_view_thread = None

def get_image():
    global camera
    global live_view_thread
    yield get_stream_frame(get_jpeg_for_message("Loading..."))
    # Connect to the first camera we can find.
    while True:
        try:
            cameras = pysony.ControlPoint().discover()
        except OSError as e:
            msg = str(e)
            app.logger.error(msg)
            yield get_stream_frame(get_jpeg_for_message(msg))
            time.sleep(1)
            continue
        msg = f'{len(cameras)} camera(s) discovered.'
        app.logger.info(msg)
        if len(cameras) == 0:
            yield get_stream_frame(get_jpeg_for_message(msg))
            # time.sleep(1) no need for a sleep here; discover() takes a while.
            continue
        break

    app.logger.info(f'Connecting to camera at {cameras[0]}...')
    camera = pysony.SonyAPI(cameras[0])

    # The following squence was tested with an A7RII
    # Put the camera in capture mode.
    app.logger.info(f'Placing camera in capture mode...')
    result = camera.startRecMode()
    msg = sony_error(result)
    if msg:
        yield get_stream_frame(get_jpeg_for_message(msg + '\nRefresh the page.'))
        return

    while True:
        result = camera.startLiveview()
        msg = sony_error(result)
        if msg:
            yield get_stream_frame(get_jpeg_for_message(msg))
            time.sleep(1)
            continue
        break
    live_view_thread = pysony.SonyAPI.LiveviewStreamThread(camera.liveview())
    live_view_thread.start() # Start receiving from the stream.
    while True:
        jpeg_data = live_view_thread.get_latest_view()
        yield get_stream_frame(jpeg_data)

@app.route('/liveview')
def liveview():
    return Response(get_image(), mimetype=f'multipart/x-mixed-replace; boundary={_multipart_boundary}')

last_photo_url = None

def take_photo():
    global last_photo_url
    if not camera:
        return 'Not connected to a camera!', 500
    msg = sony_error(camera.actTakePicture()) # evidently, in some cameras, this isn't blocking.
    if msg:
        return msg, 500
    result = camera.awaitTakePicture() # so we add this. Both return the URL where we can retrieve the photo.
    msg = sony_error(result)
    if msg:
        return msg, 500
    try:
        last_photo_url = result['result'][0][0]
    except:
        return 'Could not retrieve URL of last photo.', 500
    app.logger.info(f'Photo captured and stored at {last_photo_url}')
    # Prevent reloading the index page by returning 204.
    # from https://stackoverflow.com/a/46253885/149506
    return '', 204

def view_photo():
    global last_photo_url
    if not last_photo_url:
        return '', 204 # fail quietly.
    # This is a convenient, if annoying, way to open a new tab with the image.
    webbrowser.open_new_tab(last_photo_url)
    return '', 204

    # Otherwise, we can retrieve the image data and send it as a response. but 
    # that will require hitting back on the browser which will re-initialize
    # the camera.
    img_data = requests.get(last_photo_url).content
    mem_file = BytesIO()
    mem_file.write(img_data)
    mem_file.seek(0)
    global live_view_thread
    if live_view_thread:
        # We need to stop the thread because we're navigating away from the page.
        # Otherwise, if someone presses the back button, you'll start a second thread
        # and end up in an exception
        live_view_thread.stop() 
    return send_file(mem_file, mimetype='image/jpeg')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    if request.method == 'POST':
        if 'take_photo' in request.form:
            app.logger.info('Take a photo!')
            return take_photo()
        if 'view_photo' in request.form:
            app.logger.info('View photo!')
            return view_photo()