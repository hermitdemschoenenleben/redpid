import pickle
import numpy as np
import subprocess
from matplotlib import pyplot as plt
from matplotlib import gridspec
from osci_to_frequency import do

import seaborn as sns
sns.set_context("talk", font_scale=0.8)
#sns.set()

LENGTH = 131.072e-6
FPS = 40

gs = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1.5])

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

    center_current = 125

    for i, d in enumerate(control):
        if i == 0:
            # invent a "zero" line
            yield (times, [center_current] * len(d))

        # convert to volt
        d = [c / 8192 for c in d]
        d = [
            center_current - (v * 50) for v in d
        ]

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

        if i == 0:
            # invent a "zero" line
            yield (
                [_ / 1e-6 for _ in times[-1]],
                [np.mean([_  / 1e8 for _ in data[-1] if not np.isnan(_)])] * len(data[-1])
            )

        yield [_ / 1e-6 for _ in times[-1]], [_ / 1e8 for _ in data[-1]]

    plt.show()


def get_fn(i):
    return 'exported/%s.png' % (
        ('000000' + str(i))[-5:]
    )


def plot_control_signal_and_frequencies(folder):
    time_length = 190

    for i, [[times_c, control], [times_f, frequencies]] in enumerate(zip(
            iterate_over_control_signals(folder),
            iterate_over_frequencies(folder + 'frequencies/')
    )):
        plt.clf()

        # plot control signal
        ax = plt.subplot(gs[1])

        #plt.grid()
        ax.xaxis.grid(True)
        plt.plot(times_c + [_ + times_c[-1] for _ in times_c], control * 2)
        plt.ylim((60, 190))
        plt.xlim((0, time_length))
        #plt.xticks(time_ticks)
        #plt.xlim((0, LENGTH / 1e-6))
        plt.yticks((75, 100, 125, 150, 175))
        plt.xlabel('time in us')


        plt.ylabel('inj. current in mA')
        #plt.tight_layout()

        # plot frequencies
        ax = plt.subplot(gs[0])
        ax.get_yaxis().set_label_coords(-.08,0.5)
        ax.xaxis.grid(True)
        #plt.grid()

        plt.ylabel('beat note in GHz')
        len_f = int(len(times_f) / 200 * time_length)
        shift = 9

        plt.plot((-1000, 10000), (6.835, 6.835), 'k--')
        plt.plot((-1000, 10000), (.25, .25), 'k--')

        plt.plot(times_f[:len_f], frequencies[shift:shift + len_f])
        plt.ylim((-0.5, 7.5))
        plt.xlim((0, time_length))
        plt.xticks(visible=False)


        def figsize(ratio=1.33, figwidth=None, figheigth=None):
            """
            Returns a tuple for setting the figsize argument of matplotlib's subfigure
            function.

            Parameters
            ----------
            ratio : float (default 1.33)
                The ratio figwidth / fighheight. Default is 4/3
            figwidth, fighheight : (optional)
                Figure width or height in inches. Either one can be set and the other
                one will be set based on `ratio`. If none are given, the current global
                value of the figure width will be used.

            Returns
            -------
            (figwidth, figheigth) : tuple
            """
            if not figwidth is None:
                figheigth = figwidth / ratio
            elif not figheigth is None:
                figwidth = figheigth * ratio
            if (figwidth is None) and (figheigth is None):
                figwidth = plt.rcParams['figure.figsize'][0]
                figheigth = figwidth / ratio

            return (figwidth, figheigth)

        plt.gcf().set_size_inches(*figsize(1))


        plt.tight_layout()
        plt.title('%.1f s' % (i / FPS))
        plt.savefig(folder + get_fn(i))


    # save the last frame several times
    for j in range(1000):
        plt.savefig(folder + get_fn(i + j))


def images_to_mp4(folder):
    subprocess.Popen(
        'ffmpeg -y -framerate %d -i %s/exported/%%05d.png -c:v libx264 -profile:v high '
        '-crf 20 -pix_fmt yuv420p %s/output.mp4' % (FPS, folder, folder),
        shell=True
    )


if __name__ == '__main__':
    folder = '/media/depot/data-2019/afmot/jump-generation/'
    plot_control_signal_and_frequencies(folder)
    images_to_mp4(folder)
