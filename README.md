# ASRClient [for KOREAN Language]

PREREQUEST

#python 2.7

#python -m pip install pyaudio

#python -m pip install --user ws4py==0.3.2

STEPS

Record 5 seconds, and STT:
python ASRClient_py27.py -u ws://dsvmyoh3aeorn6p3o.eastus.cloudapp.azure.com:8080/client/ws/speech ./output.wav

Use sample speech to test STT:
python ASRClient_py27.py -u ws://dsvmyoh3aeorn6p3o.eastus.cloudapp.azure.com:8080/client/ws/speech ./sample.flac
