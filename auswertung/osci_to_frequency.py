import csv
import pickle
import numpy as np
from time import sleep
from scipy.signal import stft, find_peaks_cwt
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt
from multiprocessing import Pool

#TARGET_FREQUENCIES = [1339, 5490]
TARGET_FREQUENCIES = [6835, 250]
TARGET_AVERAGING_TIME = 1e-6
N_SHIFTS = 10
PRESCALER = 10

def load_data(filename):
    #with open('hohesamplingrate.csv', 'r') as f:
    with open(filename, 'r') as f:
        r = csv.reader(f)

        times = []
        y = []

        for i, row in enumerate(r):
            # skip header
            if i > 5:
                time_ = float(row[3])

            if i == 6:
                start_time = time_

            #if time_ - start_time > 1e-4:
            #    break

            times.append(float(row[3]))
            y.append(float(row[4]))

    times = [_ - times[0] for _ in times]

    return times, y


def nan_helper(y):
    """Helper to handle indices and logical indices of NaNs.

    Input:
        - y, 1d numpy array with possible NaNs
    Output:
        - nans, logical indices of NaNs
        - index, a function, with signature indices= index(logical_indices),
          to convert logical indices of NaNs to 'equivalent' indices
    Example:
        >>> # linear interpolation of NaNs
        >>> nans, x= nan_helper(y)
        >>> y[nans]= np.interp(x(nans), x(~nans), y[~nans])
    """

    return np.isnan(y), lambda z: z.nonzero()[0]


def parabolic(f, x):
    """Quadratic interpolation for estimating the true position of an
    inter-sample maximum when nearby samples are known.

    f is a vector and x is an index for that vector.

    Returns (vx, vy), the coordinates of the vertex of a parabola that goes
    through point x and its two neighbors.

    Example:
    Defining a vector f with a local maximum at index 3 (= 6), find local
    maximum if points 2, 3, and 4 actually defined a parabola.

    In [3]: f = [2, 3, 1, 6, 4, 2, 3, 1]

    In [4]: parabolic(f, argmax(f))
    Out[4]: (3.2142857142857144, 6.1607142857142856)

    """
    xv = 1/2. * (f[x-1] - f[x+1]) / (f[x-1] - 2 * f[x] + f[x+1]) + x
    yv = f[x] - 1/4. * (f[x-1] - f[x+1]) * (xv - x)
    return (xv, yv)


def fft(data, samplerate, N_per_segment):
    f, t, Zxx = stft(data, samplerate, nperseg=N_per_segment)
    frequencies = []
    real = []

    #plt.pcolormesh(t, f, np.abs(Zxx))
    #plt.ylim((0, 7.2e9))
    #plt.show()

    maximum_values = []

    for idx in range(Zxx.shape[1]):
        spectrum = Zxx[:, idx]

        # ignore maxima close to 0
        ignore_maxima_idx = 10

        maximum_idx = np.argmax(abs(spectrum[ignore_maxima_idx:])) + ignore_maxima_idx
        real_maximum = parabolic(np.log(abs(spectrum)), maximum_idx)[0]

        real_maximum *= (f[1] - f[0])
        maximum = maximum_idx * (f[1] - f[0])

        frequencies.append(maximum)
        real.append(real_maximum)
        maximum_values.append(np.abs(spectrum[maximum_idx]))

    # ignore values where the spectrum is very weak
    # interpolate instead
    frequencies = np.array(frequencies)
    frequencies[np.array(maximum_values) < 0.01] = np.nan
    nans, times= nan_helper(frequencies)
    frequencies[nans]= np.interp(times(nans), times(~nans), frequencies[~nans])

    return t, frequencies


def plot_data(times, frequencies, *args, **kwargs):
    times = [t / 1e-6 for t in times]
    frequencies = [f * PRESCALER for f in frequencies]

    plt.plot(times, [f / 1e9 for f in frequencies], *args, **kwargs)
    plt.xlabel('time in microseconds')
    plt.ylabel('frequency in GHz')
    plt.grid()
    plt.xticks(np.arange(0, 200, 10))


def sin(t, a, w, phase, shift):
    return a * np.sin(2 * np.pi * w * t + phase) + shift


def do_fit(times_slice, data_slice, guess):
    try:
        popt, pcov = curve_fit(
            sin,
            times_slice,
            data_slice,
            [0.1, guess, 0, 0]
        )
        a, w, phase, shift = popt
        return w, np.sqrt(np.diag(pcov))[1]
    except:
        print('fit failed')
        return np.nan, np.nan


def fit_sine_to_data(data, N_per_segment, frequencies_fft, times):
    N_segments = int(len(data) / N_per_segment)

    f_end = []
    err_end = []
    backup = []

    pool = Pool(5)

    results = []
    times_fit = []

    for N in range(N_segments - 1):
        start_idx = N_per_segment * N
        end_idx = N_per_segment * (N + 1)

        current_fft = frequencies_fft[N * 2]

        for shift in range(N_SHIFTS):
            start_idx2 = start_idx + int(shift * N_per_segment / N_SHIFTS)
            end_idx2 = start_idx2 + int(N_per_segment / 2)

            times_slice = np.array(times[start_idx2:end_idx2])
            data_slice = np.array(data[start_idx2:end_idx2])
            #print(int(np.mean([start_idx2, end_idx2]))-1, len(times))
            times_fit.append(
                times[int(np.mean([start_idx2, end_idx2]))]
            )

            results.append(
                pool.apply_async(do_fit, (times_slice, data_slice, current_fft))
            )
            backup.append(current_fft)

    while True:
        count = len(results)
        ready_count = len([r for r in results if r.ready()])
        print('%d of %d ready' % (ready_count, count))
        sleep(1)

        if count == ready_count:
            break

    pool.close()
    pool.join()

    for N, r in enumerate(results):
        freq, err = r.get()
        f_end.append(freq)
        err_end.append(err)

    err_end = np.array(err_end)
    f_end = np.array(f_end)

    return times_fit, f_end, backup, err_end


def do(filename, use_cache, show_plot, skip_fit=False):
    rv = {}

    if not use_cache:
        times, data = load_data(filename)
        delta_t = (times[1] - times[0])
        N_per_segment = int(TARGET_AVERAGING_TIME / delta_t)
        total_t = delta_t * len(times)
        samplerate = 1 / delta_t

        times_fft, frequencies_fft = fft(data, samplerate, N_per_segment)

        plot_data(times_fft, frequencies_fft, linewidth=2)
        if show_plot:
            plt.show()
        else:
            plt.clf()

        if not skip_fit:
            times_fit, frequencies_fit, backup_frequencies, err_fit = fit_sine_to_data(data, N_per_segment, frequencies_fft, times)

            # filter out values with high fitting uncertainities and replace them
            # with the corresponding FFT values
            err_median = np.median([e for e in err_fit if not np.isnan(e)])
            to_filter = err_fit > 5 * err_median
            frequencies_fit[to_filter] = np.nan


            # choose the values obtained by the fit when possible and use the FFT values
            # otherwise
            combined = [
                fit
                if fit and not np.isnan(fit)
                else fft
                for fit, fft in zip(frequencies_fit, backup_frequencies)
            ]
        else:
            times_fit = []
            frequencies_fit = []
            combined = frequencies_fft

        with open(filename + '.cache', 'wb') as f:
            pickle.dump({
                'times_fit': times_fit,
                'times_fft': times_fft,
                'frequencies_fft': frequencies_fft,
                'frequencies_fit': frequencies_fit,
                'combined': combined
            }, f)

    with open(filename + '.cache', 'rb') as f:
        cache = pickle.load(f)
        times_fit = cache['times_fit']
        times_fft = cache['times_fft']
        frequencies_fft = cache['frequencies_fft']
        f_end = cache['frequencies_fit']
        combined = cache['combined']

    plot_data(times_fft, frequencies_fft, label='fft')
    if not skip_fit:
        plot_data(times_fit, combined, label='combined')
        plot_data(times_fit, f_end, label='fit')
    #plt.plot(times_fit, [1e4 * _ for _ in err_end], label='errors')
    plt.legend()
    plt.xticks([0, 25, 50, 75, 100, 125, 150, 175, 200])
    plt.savefig(filename + '.frequencies.svg')
    if show_plot:
        plt.show()
    else:
        plt.clf()

    def apply_prescaler(f):
        return [_ * PRESCALER for _ in f]

    combined = apply_prescaler(combined)
    frequencies_fft = apply_prescaler(frequencies_fft)
    f_end = apply_prescaler(f_end)

    if not skip_fit:
        bin_max = 10e9
        # 1 MHz size
        N_bins = 10000
        hist, bin_edges = np.histogram(combined, N_bins, (0, bin_max))
        # in MHz
        bin_positions = list(range(len(hist)))

        ranges = (0, 3, 6, 10)
        total_in_range = [0] * len(ranges)

        for i, target in enumerate(TARGET_FREQUENCIES):
            print('target frequency', target, ' MHz:')
            idxs = (target - 50, target + 50)
            hist_slice = hist[idxs[0]:idxs[1]]
            max_idx = np.argmax(hist_slice)
            all_close_to_max = np.sum(hist_slice)

            for range_idx, range_ in enumerate(ranges):
                in_range = np.sum(hist_slice[max_idx - range_ : max_idx + range_ +1])
                percentage = in_range / all_close_to_max * 100
                total_in_range[range_idx] += in_range
                rv['target_%d_range_%d' % (i, range_)] = percentage
                print('± %d MHz: %.0f %%' % (range_, percentage))

        print('in total close to any of the frequencies:')
        for range_idx, range_ in enumerate(ranges):
            percentage = total_in_range[range_idx] / len(combined) * 100
            rv['total_close_%d' % range_] = percentage
            print('± %d MHz: %.0f %%' % (range_, percentage))


        plt.plot(bin_positions, hist)

        rv.update({
            'bin_positions': bin_positions,
            'histogram': hist
        })
        if show_plot:
            plt.show()
        else:
            plt.clf()

    rv.update(cache)
    return rv


"""
if __name__ == '__main__':
    filename = '/home/ben/data/afmot/zweiseitiger-test-2/algo-no-pid.csv'
    filename = '/media/depot/data/MA/jump_lock_continuous/neu-shift2.csv'
    filename = '/media/depot/data/MA/jump_lock_continuous/with-integrator/endCH1.csv'
    filename = '/media/depot/data/MA/jump_lock_continuous/without-integrator/endCH1.csv'
    filename = '/home/ben/data/afmot/zweiseitiger-test-2/hohesamplingrate.csv'

    show_plot = False
    use_cache = False

    data = []

    delays = [1, 3, 5, 7, 10, 15, 25, 50, 100, 150, 200, 250, 400]
    #for wait in (3.5, 4.5, 5.5, 6.5):
    for decimation in (0, 1, 2, 3, 4, 5):
        d = []
        for delay in delays:
            filename = '/media/depot/data/2019/afmot/decimation_curvdelay/decimation_%d_curvdelay_%dCH2.csv' % (decimation, delay)
            print(decimation, delay)
            try:
                d.append(
                    do(filename, True, False)
                )
            except:
                print('skipping', decimation, delay)
                continue

        data.append(d)

    for data2 in data:
        plt.plot(list(d['total_close_6'] for d in data2))

    plt.show()
"""
