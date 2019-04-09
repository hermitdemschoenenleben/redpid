import time
import numpy as np
import pickle
import subprocess
from os import path
from devices import connect_to_device_service

REPLAY_SHIFT = -200-24
LENGTH = 16384
N_BITS = 14
MAX_STATE = 4
N_STATES = MAX_STATE + 1
ONE_ITERATION = 16384 * N_STATES
BASE_FREQ = 7629.394531249999
ITERATIONS_PER_SECOND = BASE_FREQ / N_STATES
ONE_SECOND = ONE_ITERATION * ITERATIONS_PER_SECOND
ONE_MS = ONE_SECOND / 1000
COOLING_PIN = 'gpio_n_do3_en'
CAM_TRIG_PIN = 'gpio_n_do4_en'
REPUMPING_PIN = 'gpio_n_do5_en'
END_DELAY = 5000 * ONE_SECOND


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


def reset_fpga(host, user, password):
    ssh_cmd='sshpass -p %s ssh %s@%s' % (password, user, host)
    reset_cmd="/bin/bash /reset.sh"
    p = subprocess.Popen(' '.join([ssh_cmd, reset_cmd]).split(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    p.wait()


def load_old_data(folder, filename):
    class OverrideData(Exception):
        pass

    try:
        with open(folder + filename, 'rb') as f:
            all_data = pickle.load(f)

        while True:
            append_data = input('file already exists. Append (a) or override (o) data?')
            if append_data not in ('a', 'o'):
                continue
            if append_data == 'o':
                raise OverrideData()
            else:
                break

    except (OverrideData, FileNotFoundError):
        all_data = {}

    return all_data
