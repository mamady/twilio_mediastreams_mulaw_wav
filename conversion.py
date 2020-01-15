import base64
import json
import logging

from flask import Flask
from flask_sockets import Sockets

import pyaudio
import subprocess
import os

app = Flask(__name__)
sockets = Sockets(app)
HTTP_SERVER_PORT = 5000

"""
The websocket setup is borrowed from here:  https://github.com/TwilioDevEd/mediastreams-consume-websockets-flask. Point your Twilio mediastreams websocket to the machine running this code (ngrok makes this easy).

There is very little documentation online on how to convert Twilio mediastreams mulaw format into anything
that resembles a modern standard for audio.


Twilio sends the mediastream data in a constant stream of chunked mulaw data encoded in base64. We pipe this data into ffmpeg,  and then get the output from ffmpeg all in memory and stdout/stdin subprocess writes/reads (no scratch files are written). Hopefully it is useful....
"""

@sockets.route('/media')
def echo(ws):
    app.logger.info("connection init")
    counter = 0

    """begin audio channel setup"""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=8000,
                        output=True)

    # this is how BR works right ... ?
    # 4096 seems to work just right here. 2048 is too low i think
    BITRATE = 4096
    """end audio"""

    # magic command to convert random 8kbit mulaw to wav
    # takes mulaw from stdin (which we write in at about a rate of 4k
    # 4k is quick enough where we can still hear the music in "real time"
    # but not stress out the computer too much ... not sure about all the maths
    # here but it works so dont change it! Lowering it may make it even quicker
    # but no need to be greedy. 

    # the 8000 is the telephony mulaw format. once we load up the pipe with 4k bytes of mulaw
    # data, then we call communicate() which will tell ffmpeg to process it. once ffmpeg processes
    # it (near instantly), we send the data to pyaudio() and then it goes to our speakers :XX

    # for Twilio:
    # right now this audio is the leg of the call that called *us*
    # that is, whoever hits our service that initiates this streaming stuff
    # otherwise we have to get into merging the streams ... that gets messy
    # but we certainly desire this at somepoint ..

    CMD = "ffmpeg -ar 8000 -f mulaw -i pipe: -f wav -"

    proc = subprocess.Popen(CMD.split(), shell=False,
                                         stdout=subprocess.PIPE,
                                         stdin=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         bufsize=1, close_fds=True)

    while not ws.closed:
        message = ws.receive()
        if message is None:
            continue

        data = json.loads(message)

        if data['event'] == "media":
            payload = data['media']['payload']
            chunk = base64.b64decode(payload)

            # fill this up with at least 4K bytes before we "finish"
            # the conversion with communicate() and send it to pyaudio to
            # be played
            proc.stdin.write(chunk)

            counter += len(chunk)

            # continuously stream the chunk to a file so that other
            # services / handlers can read it in real-time
            if counter > BITRATE:
                counter = 0
                out, err = proc.communicate()
                stream.write(out[128:])

                # have to recreate the process after we communicate, 
                # bc this is what the above will be writing into
                proc = subprocess.Popen(CMD.split(), shell=False,
                                                     stdout=subprocess.PIPE,
                                                     stdin=subprocess.PIPE,
                                                     stderr=subprocess.PIPE,
                                                     bufsize=1, close_fds=True)

        if data['event'] == "stop":
            app.logger.info("stopping")
            break


    stream.stop_stream()
    stream.close()
    p.terminate()

    app.logger.info("closed")


if __name__ == '__main__':
    app.logger.setLevel(logging.DEBUG)
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(('', HTTP_SERVER_PORT), app, handler_class=WebSocketHandler)
    print("Server listening on: http://localhost:" + str(HTTP_SERVER_PORT))
    server.serve_forever()
