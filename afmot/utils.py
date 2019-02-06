import numpy as np
import subprocess
from os import path
from devices import connect_to_device_service

REPLAY_SHIFT = -200-24
LENGTH = 16384

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


def acquire(N, decimation):
    stdin, stdout, stderr = pid_rp.registers.execute('/opt/redpitaya/bin/acquire %d %d' % (N, decimation))
    rows = stdout.read().strip().decode().split('\n')

    def get(row, idx):
        return int(row.strip().split(' ')[idx]) / 8191.0

    rows = [
        [get(row, 0), get(row, -1)]
        for row in rows
    ]
    return np.array(rows)


def get_shifted(d, shift):
    length = len(d)
    d = list(d) + list(d)
    d = d + d
    if shift > 0:
        return np.array(d[shift:shift + length])
    else:
        return np.array(d[length + shift:(2*length) + shift])


def save_osci(filename):
    import vxi11
    import time
    scope = vxi11.Instrument('141.20.47.204')
    scope.timeout = 10000

    while '1' in scope.ask('BUSY?'):
        # is still writing to disk, probably
        print('busy')
        time.sleep(0.5)

    scope.write('SAVE:WAVEFORM:FILEFORMAT SPREADSHEETC')
    scope.write('SAVE:WAVEFORM:SPREADSHEET:RESOLUTION FULL')

    scope.write('ACQ:STOPA SEQ')

    scope.write('ACQ:STATE ON')
    #time.sleep(1)
    #scope.write('TRIG')

    while '1' in scope.ask('ACQ:STATE?'):
        print('wait')
        time.sleep(0.5)

    scope.write('SAVE:WAVEFORM ALL, "E:/%s"' % filename)


def clock(r, percentage=.6, decimation=1):
    asg = r.asg0

    data = []

    for i in range(LENGTH):
        if i < percentage * LENGTH:
            data.append(0)
        else:
            data.append(1)

    asg.setup()
    asg.amplitude = 1
    asg.frequency = 7629.394531249999 / int(decimation)
    asg.output_direct = 'out2'
    asg.on = True
    asg.trigger_source = 'immediately'
    asg.waveform = 'dc'
    asg.data = np.array(data)


def copy_pid(r, enabled=True):
    pid = r.pid0

    pid.input = 'in1'
    pid.p = 1 if enabled else 0
    pid.output_direct = 'out1'


def replay_pyrpl(r, curve, decimation=1):
    asg = r.asg1
    """
    from matplotlib import pyplot as plt
    plt.plot(curve)
    plt.show()
    asd"""

    asg.setup()
    asg.amplitude = 1
    asg.frequency = 7629.394531249999 / decimation
    #asg.start_phase = PHASE
    multiplied_curve = []

    while len(multiplied_curve) != 16384:
        multiplied_curve += list(curve)

    #asg.start_phase = PHASE
    #asg.start_phase = 360 - (360 * PHASE / 16384)
    #asg.start_phase = 0

    asg.output_direct = 'out1'
    asg.on = True
    asg.trigger_source = 'ext_positive_edge'
    asg.waveform = 'dc'
    asg.data = np.array(multiplied_curve)