import time
import numpy as np
import subprocess
from os import path
from devices import connect_to_device_service

REPLAY_SHIFT = -200-24
LENGTH = 16384
N_BITS = 14

def do(cmd):
    subprocess.call(cmd, shell=True)


def copy_file(fn, ip):
    pth = path.join(
        *path.split(path.abspath(__file__))[:-1],
        fn
    )
    do('sshpass -p "root" scp -r %s root@%s:/jumps/' % (pth, ip))


def counter_measurement():
    counter = connect_to_device_service('192.168.1.177', 'cnt90')
    d = counter.root.frequency_measurement('C', 1e-4, 250e3)
    return list(float(f) for f in d)


def _get_osci():
    import vxi11
    scope = vxi11.Instrument('192.168.0.89')
    scope.timeout = 10000
    while '1' in scope.ask('BUSY?'):
        # is still writing to disk, probably
        print('busy')
        time.sleep(0.5)
    return scope

def arm_osci():
    scope = _get_osci()

    scope.write('SAVE:WAVEFORM:FILEFORMAT SPREADSHEETC')
    scope.write('SAVE:WAVEFORM:SPREADSHEET:RESOLUTION FULL')

    scope.write('ACQ:STOPA SEQ')

    scope.write('ACQ:STATE ON')

def save_osci(filename, force_trigger=False):
    scope = _get_osci()

    if force_trigger:
        scope.write('TRIG')

    while '1' in scope.ask('ACQ:STATE?'):
        print('wait')
        time.sleep(1)

    scope.write('SAVE:WAVEFORM ALL, "C:/Documents and Settings/TekScope_Local_Admin/Desktop/Ben/%s"' % filename)

