# Twilio Mediastreams Mulaw to Wav
hacky conversion of mulaw data (telephony standard) to wav using ffmpeg. See here https://en.wikipedia.org/wiki/%CE%9C-law_algorithm

The websocket setup is borrowed from here:  https://github.com/TwilioDevEd/mediastreams-consume-websockets-flask. Point your Twilio mediastreams websocket to the machine running this code (ngrok makes this easy).

There is very little documentation online on how to convert Twilio mediastreams mulaw format into anything
that resembles a modern standard for audio.

Twilio sends the mediastream data in a constant stream of chunked mulaw data encoded in base64. We pipe this data into ffmpeg,  and then get the output from ffmpeg all in memory and stdout/stdin subprocess writes/reads (no scratch files are written). The wav output is then streamed into a pyaudio sink, but you can write it to file and play from that in real time. 

Hopefully it is useful....
