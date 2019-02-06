import json
import numpy as np
from time import sleep
from scipy.signal import savgol_filter
from matplotlib import pyplot as plt
from os import path
import pandas
import subprocess
from devices import RedPitaya
from utils import do, get_shifted,REPLAY_SHIFT, LENGTH


def get_index_for_combining(data, filtered, max_=1, return_start_idx=False):
    direction = 1

    criterion = lambda to_check: np.abs(np.array(to_check)-max_) < 1e-3
    plateau_start = np.argmax(criterion(data))
    idx = plateau_start

    while True:
        idx += direction

        if not criterion(data[idx]):
            break

    plateau_end = idx
    print('plateau start:', plateau_start, 'end', plateau_end)

    if np.abs(plateau_start - plateau_end) < 5:
        raise Exception('no plateau')

    if return_start_idx:
        idx = plateau_start
        required_sign_changes = 0
    else:
        required_sign_changes = 2

    sign_changes = 0

    get_sign = lambda: data[idx] > filtered[idx]
    last_sign = get_sign()

    while True:
        sign = get_sign()

        if sign != last_sign:
            if sign_changes == required_sign_changes:
                break
            else:
                sign_changes += 1

        last_sign = sign
        idx += direction

    return idx


def process_control_data(combine=False, plot=False):
    with open('control_raw.json', 'r') as f:
        d = json.load(f)
        data = d['data']
        duration = d['duration']
        decimation = d['decimation']

    x_axis = np.linspace(0, duration*1e6, LENGTH)

    triggered_data = data

    mean = np.mean(triggered_data, axis=0)

    def rm(data, N=800):
        N = int(N / decimation)
        new_data = pandas.rolling_median(np.array(list(data)*5), N)
        delay = int(N/2)
        return new_data[LENGTH+delay:(2*LENGTH)+delay]

    rms = [mean]

    for n in range(5):
        rms.append(rm(rms[-1]))

    if combine:
        try:
            filtered = savgol_filter(rms[-1], 801, 3)

            combined = np.array(rms[-1])

            """plt.plot(rms[-1], label='rm')
            plt.plot(filtered, label='savgol')
            plt.show()"""

            idxs1 = (
                get_index_for_combining(rms[-1], filtered, 1),
                get_index_for_combining(np.array(list(reversed(rms[-1]))), np.array(list(reversed(filtered))), -1)
            )
            idxs2 = (
                get_index_for_combining(rms[-1], filtered, -1),
                get_index_for_combining(np.array(2 * list(reversed(rms[-1]))), np.array(2 * list(reversed(filtered))), 1) - 16384
            )

            combined[idxs1[0]:-idxs1[1]] = filtered[idxs1[0]:-idxs1[1]]
            combined[idxs2[0]:-idxs2[1]] = filtered[idxs2[0]:-idxs2[1]]

            combined[combined > 1] = 1
            combined[combined < -1] = -1

            if plot:
                plt.plot(mean, label='original')
                plt.plot(filtered, label='original + rm + savgol')
                plt.plot(rms[-1], label='original + rm')
                plt.plot(combined, label='combined')
                plt.legend()
                plt.show()

            return list(combined)
        except:
            print('no plateau found')

    with open('control.json', 'w') as f:
        json.dump({
            'duration': duration,
            'data': list(rms[-1])
        }, f)

    return list(rms[-1])

def replay_remote():
    copy_file('control.json', pid_rp_ip)
    copy_file('replay.py', pid_rp_ip)
    copy_file('start_slow_lock.py', pid_rp_ip)

    sleep(1)
    remote('replay.py')
    sleep(3)
    remote('start_slow_lock.py')


if __name__ == '__main__':
    processed = process_control_data(True, True)
    asd
    from pyrpl import Pyrpl
    p = Pyrpl('rp-f012ba.local')
    r = p.rp
    clock(r, .4)
    copy_pid(r)
    remote('prepare.py', measure_rp)
    replay_pyrpl(r, get_shifted(processed, int(REPLAY_SHIFT/DECIMATION)), DECIMATION)
    #replay_remote()