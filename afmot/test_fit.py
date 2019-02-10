import json
import numpy as np
from time import sleep
from scipy.signal import savgol_filter
from matplotlib import pyplot as plt
from os import path
import pandas
from utils import do, get_shifted, REPLAY_SHIFT, LENGTH


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
        inp_data = d['inp_data']

    x_axis = np.linspace(0, duration*1e6, LENGTH)

    #triggered_data = data

    #mean = np.mean(triggered_data, axis=0)
    mean = data

    def rm(data, N=800):
        N = int(N / decimation)
        s = pandas.Series(np.array(list(data)*5))
        new_data = s.rolling(N).median()
        #new_data = pandas.rolling_median(, N)
        delay = int(N/2)
        rv = list(new_data)[LENGTH+delay:(2*LENGTH)+delay]
        return rv

    rms = [mean]

    for n in range(5):
        rms.append(rm(rms[-1]))

    """if plot:
        for rm in rms:
            plt.plot(rm)
        plt.show()"""

    if combine:
        filtered = savgol_filter(rms[-1], 801, 3)

        combined = np.array(rms[-1])

        """plt.plot(rms[-1], label='rm')
        plt.plot(filtered, label='savgol')
        plt.show()"""

        jump_idxs = (0, 8192)

        def find_change_after_jump(data, jump_idx, max_):
            start = jump_idx + 100
            sgn = int(round(np.mean(data[start:start+10])))
            idx = start

            change_counter = 0

            while idx < max_ - 1:
                idx += 1

                if data[idx] != sgn:
                    change_counter += 1
                else:
                    change_counter = 0

                if change_counter == 3:
                    return idx
            return None


        idxs1 = (
            find_change_after_jump(inp_data, jump_idxs[0], jump_idxs[1]) or jump_idxs[1],
            jump_idxs[1],
        )
        idxs2 = (
            find_change_after_jump(inp_data, jump_idxs[1], 16383) or -1,
            -1
        )
        print('IDXS', idxs1, idxs2)

        combined[idxs1[0]:idxs1[1]] = filtered[idxs1[0]:idxs1[1]]
        combined[idxs2[0]:idxs2[1]] = filtered[idxs2[0]:idxs2[1]]

        good_idxs = (1000, 7000)
        good_data = combined[good_idxs[0]:good_idxs[1]]

        def func(x, a, b, c, d):
            print(x, a, b, c)
            return a + b * x + c * (x**2) + d * (x**3)

        from scipy.optimize import curve_fit
        xdata = np.array(range(len(good_data))) + good_idxs[0]
        print(xdata)

        popt, pcov = curve_fit(func, np.array(xdata), np.array(good_data))
        ext_xdata = np.linspace(0, 8192)
        plt.plot(ext_xdata, func(ext_xdata, *popt), label='fit')
        #plt.plot(xdata, good_data)
        #plt.show()

        if plot:
            plt.plot(mean, label='original')
            plt.plot([_ * 8192 for _ in inp_data], label='input data')
            plt.plot(filtered, label='original + rm + savgol')
            plt.plot(rms[-1], label='original + rm')
            plt.plot(combined, label='combined')
            plt.legend()
            plt.show()

        return list(combined)

    with open('control.json', 'w') as f:
        json.dump({
            'duration': duration,
            'data': list(rms[-1])
        }, f)

    return list(rms[-1])


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