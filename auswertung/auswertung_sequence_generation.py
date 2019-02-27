import pickle
import numpy as np
import subprocess
from matplotlib import pyplot as plt
from osci_to_frequency import do

import seaborn as sns
sns.set_context("talk", font_scale=0.8)
#sns.set()

LENGTH = 131.072e-6

def iterate_over_control_signals(folder):
    filename = folder + 'control-signal.pickle'

    with open(filename, 'rb') as f:
        d = pickle.load(f)

    control = d['control_signals']

    max_points = 16384
    times = list(
        (t * LENGTH / max_points) / 1e-6 * (max_points / len(control[0]))
        for t in
        range(len(control[0]))
    )
    time_ticks = np.arange(0, 160, 20)

    for i, d in enumerate(control):
        # convert to volt
        d = [c / 8192 for c in d]

        yield (times, d)


def iterate_over_frequencies(folder):
    show_plot = False

    data = []
    times = []

    for i, n in enumerate(list(int(_) for _ in np.arange(50, 11851, 50))):
        print(i, n)

        fn = 'development_%sCH2.csv' % n

        for use_cache in (True, False):
            try:
                result = do(folder + fn, use_cache, show_plot, skip_fit=True)
                data.append(result['frequencies_fft'])
                times.append(result['times_fft'])
                break
            except Exception as e:
                print(e)
                if not use_cache:
                    print('skipping', n)

        yield [_ / 1e-6 for _ in times[-1]], [_ / 1e8 for _ in data[-1]]

    plt.show()


def plot_control_signal_and_frequencies(folder):
    for i, [[times_c, control], [times_f, frequencies]] in enumerate(zip(
            iterate_over_control_signals(folder),
            iterate_over_frequencies(folder + 'frequencies/')
    )):
        # plot control signal
        ax = plt.subplot(2, 1, 1)

        plt.grid()
        plt.plot(times_c, control)
        plt.ylim((-1.1, 1.1))
        plt.xlim((0, 131))
        #plt.xticks(time_ticks)
        #plt.xlim((0, LENGTH / 1e-6))
        plt.yticks((-1, -.5, 0, .5, 1))
        plt.xticks(visible=False)

        plt.ylabel('control sig. in V')
        #plt.tight_layout()

        # plot frequencies
        ax = plt.subplot(2, 1, 2)
        ax.get_yaxis().set_label_coords(-.08,0.5)
        plt.grid()

        plt.xlabel('time in us')
        plt.ylabel('beat note in GHz')
        len_f = int(len(times_f) / 200 * 131)
        shift = 9
        plt.plot(times_f[:len_f], frequencies[shift:shift + len_f])
        plt.ylim((0, 7))
        plt.xlim((0, 131))


        fn = ('000000' + str(i))[-5:]
        plt.tight_layout()
        plt.savefig(folder + 'exported/%s.png' % fn)
        plt.clf()


def images_to_mp4(folder):
    subprocess.Popen(
        'ffmpeg -framerate 40 -i %s/exported/%%05d.png -c:v libx264 -profile:v high '
        '-crf 20 -pix_fmt yuv420p %s/output.mp4' % (folder, folder),
        shell=True
    )


if __name__ == '__main__':
    folder = '/media/depot/data-2019/afmot/jump-generation/'
    plot_control_signal_and_frequencies(folder)
    images_to_mp4(folder)
