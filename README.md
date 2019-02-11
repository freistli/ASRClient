# ASRClient

Record and send 16k rate .wav to ASR server and get response in UTF-8

## PREREQUEST

### python 2.7 (>=2.7.12)

### python -m pip install pyaudio

Refer to: http://people.csail.mit.edu/hubert/pyaudio/

### python -m pip install --user ws4py==0.3.2

## STEPS of Using Websocket

### On Linux:

Record 5 seconds, and STT:

python ASRClient_py27.py -u ws://[server]/client/ws/speech ./output.wav

Use sample speech to test STT:

python ASRClient_py27.py -u ws://[server]/client/ws/speech ./sample.flac

### On Windows

In Command Window, run to use UTF-8 codepage:

chcp 65001

And then run:

Record 5 seconds, and STT:

python ASRClient_py27.py -u ws://[server]/client/ws/speech ./output.wav

Use sample speech to test STT:

python ASRClient_py27.py -u ws://[server]/client/ws/speech ./sample.flac

## Steps of Using HTTP service
curl -T sample.flac "http://[server]/client/dynamic/recognize"


## REFERENCE

https://github.com/alumae/kaldi-gstreamer-server
