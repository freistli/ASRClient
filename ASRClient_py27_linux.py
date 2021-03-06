# -*- coding: utf-8 -*-
#python 2.7
#python -m pip install pyaudio
#python -m pip install --user ws4py==0.3.2
#python -m pip install requests
#install audiotools http://audiotools.sourceforge.net/ 

import pyaudio
import wave
import argparse
from ws4py.client.threadedclient import WebSocketClient
import time
import threading
import sys
import urllib
import Queue
import json
import time
import os
import subprocess
import shlex
import ast
import requests
import audiotools

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 16000
RECORD_SECONDS = 3
WAVE_OUTPUT_FILENAME = r".\output.wav"

def wav2flac (filepath_wav = WAVE_OUTPUT_FILENAME):
    audiofile = ''
    if filepath_wav.endswith(".wav"):
        compression_quality = '0'
        filepath_flac = filepath_wav.replace(".wav", ".flac")
        audiotools.open(filepath_wav).convert(filepath_flac, audiotools.FlacAudio, compression_quality)
        audiofile = open (filepath_flac,'rb')
    else:
        audiofile = open (filepath_wav,'rb')
    return audiofile

def RecordVoice(path = WAVE_OUTPUT_FILENAME):
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

    print("* recording")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()



def rate_limited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)
    def decorate(func):
        lastTimeCalled = [0.0]
        def rate_limited_function(*args,**kargs):
            elapsed = time.clock() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait>0:
                time.sleep(leftToWait)
            ret = func(*args,**kargs)
            lastTimeCalled[0] = time.clock()
            return ret
        return rate_limited_function
    return decorate


class MyClient(WebSocketClient):

    def __init__(self, audiofile, url, protocols=None, extensions=None, heartbeat_freq=None, byterate=32000,
                 save_adaptation_state_filename=None, send_adaptation_state_filename=None):
        super(MyClient, self).__init__(url, protocols, extensions, heartbeat_freq)
        self.final_hyps = []
        self.audiofile = audiofile
        self.byterate = byterate
        self.final_hyp_queue = Queue.Queue()
        self.save_adaptation_state_filename = save_adaptation_state_filename
        self.send_adaptation_state_filename = send_adaptation_state_filename

    @rate_limited(4)
    def send_data(self, data):
        self.send(data, binary=True)

    def opened(self):
        #print "Socket opened!"
        def send_data_to_ws():
            if self.send_adaptation_state_filename is not None:
                print >> sys.stderr, "Sending adaptation state from %s" % self.send_adaptation_state_filename
                try:
                    adaptation_state_props = json.load(open(self.send_adaptation_state_filename, "r"))
                    self.send(json.dumps(dict(adaptation_state=adaptation_state_props)))
                except:
                    e = sys.exc_info()[0]
                    print >> sys.stderr, "Failed to send adaptation state: ",  e
            with self.audiofile as audiostream:
                for block in iter(lambda: audiostream.read(self.byterate/4), ""):
                    self.send_data(block)
            print >> sys.stderr, "Audio sent, now sending EOS"
            self.send("EOS")

        t = threading.Thread(target=send_data_to_ws)
        t.start()


    def received_message(self, m):
        response = json.loads(str(m))
        #print >> sys.stderr, "RESPONSE:", response
        #print >> sys.stderr, "JSON was:", m
        if response['status'] >= 0:
            if 'result' in response:
                trans = response['result']['hypotheses'][0]['transcript']
                if response['result']['final']:
                    #print >> sys.stderr, trans,
                    self.final_hyps.append(trans)
                    print >> sys.stderr, '\r%s' % trans.replace("\n", "\\n").encode('utf-8')
                else:
                    print_trans = trans.replace("\n", "\\n")
                    if len(print_trans) > 80:
                        print_trans = "... %s" % print_trans[-76:].encode('utf-8')
                    print >> sys.stderr, '\r%s' % print_trans.encode('utf-8'),
            if 'adaptation_state' in response:
                if self.save_adaptation_state_filename:
                    print >> sys.stderr, "Saving adaptation state to %s" % self.save_adaptation_state_filename
                    with open(self.save_adaptation_state_filename, "w") as f:
                        f.write(json.dumps(response['adaptation_state']))
        else:
            print >> sys.stderr, "Received error from server (status %d)" % response['status']
            if 'message' in response:
                print >> sys.stderr, "Error message:",  response['message'].encode('utf-8')


    def get_full_hyp(self, timeout=60):
        return self.final_hyp_queue.get(timeout)

    def closed(self, code, reason=None):
        #print "Websocket closed() called"
        #print >> sys.stderr
        self.final_hyp_queue.put(" ".join(self.final_hyps))

def RunWSClient(args):    
    content_type = args.content_type
    if content_type == '' and args.audiofile.endswith(".raw"):
        content_type = "audio/x-raw, layout=(string)interleaved, rate=(int)%d, format=(string)S16LE, channels=(int)1" %(args.rate/2)
    audiofile = wav2flac (args.audiofile)
    ws = MyClient(audiofile, args.uri + '/client/ws/speech' + '?%s' % (urllib.urlencode([("content-type", content_type)])), byterate=args.rate,
                  save_adaptation_state_filename=args.save_adaptation_state, send_adaptation_state_filename=args.send_adaptation_state)
    ws.connect()
    result = ws.get_full_hyp()
    print result.encode('utf-8')

def RunHTTPClient(args):
    audiofile = wav2flac (args.audiofile)
    r = requests.put(args.uri + '/client/dynamic/recognize', data=audiofile)
    res = r.content.decode('unicode_escape').encode('utf-8')
    data = json.loads(res)    
    #print (res)
    print (data['hypotheses'][0]['utterance'].encode('utf-8'))

def main():

    parser = argparse.ArgumentParser(description='Command line client for kaldigstserver')
    parser.add_argument('-u', '--uri', default="http://localhost:8888/", dest="uri", help="Server HTTP URI")
    parser.add_argument('-r', '--rate', default=32000, dest="rate", type=int, help="Rate in bytes/sec at which audio should be sent to the server. NB! For raw 16-bit audio it must be 2*samplerate!")
    parser.add_argument('--save-adaptation-state', help="Save adaptation state to file")
    parser.add_argument('--send-adaptation-state', help="Send adaptation state from file")
    parser.add_argument('--content-type', default='', help="Use the specified content type (empty by default, for raw files the default is  audio/x-raw, layout=(string)interleaved, rate=(int)<rate>, format=(string)S16LE, channels=(int)1")
    #parser.add_argument('audiofile', help="Audio file to be sent to the server", type=argparse.FileType('rb'), default=sys.stdin)
    parser.add_argument('audiofile', help="Audio file to be sent to the server")

    args = parser.parse_args()

    #RecordVoice()    

    if args.uri.startswith('ws'):
        RunWSClient(args)       
    if args.uri.startswith('http'):
        RunHTTPClient(args)

if __name__ == "__main__":
    main()
