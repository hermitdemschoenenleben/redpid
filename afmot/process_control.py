import json
import pandas
import numpy as np
from time import sleep
from matplotlib import pyplot as plt
from scipy.signal import savgol_filter

from utils import do, LENGTH


def load_data(filename):
    with open(filename, 'r') as f:
        print('LOAD', filename)
        d = json.load(f)
        control_data = d['data']
        duration = d['duration']
        decimation = d.get('decimation', 1)
        error_signal = d['inp_data']

    return control_data, error_signal, duration, decimation


def rolling_median(data, N=800, decimation=1):
    s = pandas.Series(np.array(list(data)*5))
    new_data = list(s.rolling(N).median())
    delay = int(N/2)
    return new_data[LENGTH+delay:(2*LENGTH)+delay]


def find_change_after_jump(error_signal, jump_idx, max_idx, skip_after_jump=75,
                           N_consecutive_changes=3):
    start = jump_idx + skip_after_jump
    sgn = int(round(
        np.mean(error_signal[start:start+10])
    ))

    idx = start
    change_counter = 0

    while idx < max_idx - 1:
        idx += 1

        if error_signal[idx] != sgn:
            change_counter += 1
        else:
            change_counter = 0

        if change_counter == N_consecutive_changes:
            return idx

    return None


def process_control_data(filename='control_raw.json', combine=False, plot=False):
    control_data, error_signal, duration, decimation = load_data(filename)

    # apply rolling mean several times
    rms = [control_data]
    for n in range(5):
        rms.append(rolling_median(rms[-1], decimation=decimation))
    rm_filtered = rms[-1]

    if combine:
        savgol_filtered = savgol_filter(rm_filtered, 801, 3)
        combined = np.array(rm_filtered)

        jump_idxs = (0, 8192)

        idxs1 = (
            find_change_after_jump(error_signal, jump_idxs[0], jump_idxs[1]) or jump_idxs[1],
            jump_idxs[1],
        )
        idxs2 = (
            find_change_after_jump(error_signal, jump_idxs[1], 16383) or -1,
            -1
        )

        combined[idxs1[0]:idxs1[1]] = savgol_filtered[idxs1[0]:idxs1[1]]
        combined[idxs2[0]:idxs2[1]] = savgol_filtered[idxs2[0]:idxs2[1]]

        if plot:
            plt.plot(control_data, label='original')
            plt.plot([_ * 8192 for _ in error_signal], label='input data')
            plt.plot(savgol_filtered, label='original + rm + savgol')
            plt.plot(rm_filtered, label='original + rm')
            plt.plot(combined, label='combined')
            plt.legend()
            plt.show()

        return list(combined)

    return list(rm_filtered)


if __name__ == '__main__':
    processed = process_control_data('control_raw.json', combine=True, plot=True)
