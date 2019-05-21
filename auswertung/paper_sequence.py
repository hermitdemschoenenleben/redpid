import pickle
import numpy as np
import subprocess
from matplotlib import pyplot as plt
from matplotlib import gridspec
from osci_to_frequency import do
from ben.plot import plt, save_paper, gridspec, set_font_scale, set_font_size
from ben.mplstyles import figsize
from ben.utils.plot import set_aspect


FONT_SIZE = 16
INSET_COLOR = '#fff4f4'

set_font_size(FONT_SIZE)
plt.gcf().set_size_inches(*figsize(1.3))

LENGTH = 131.072e-6

column = gridspec.GridSpec(2, 1, height_ratios=[2, 1.2])

def get_control_signal(folder):
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

    d = control[-1]

    # convert to volt
    d = [c / 8192 for c in d]
    d = [
        center_current - (v * 50) for v in d
    ]

    return (times, d)


def get_frequencies(folder):
    data = []
    times = []

    show_plot = False

    n = list(int(_) for _ in np.arange(50, 11851, 50))[-1]

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



    return [_ / 1e-6 for _ in times[-1]], [_ / 1e8 for _ in data[-1]]


def get_fn(i):
    return 'exported/%s.png' % (
        ('000000' + str(i))[-5:]
    )


def plot_control_signal_and_frequencies(folder):
    time_length = 190

    [times_c, control] = get_control_signal(folder)
    [times_f, frequencies] = get_frequencies(folder + 'frequencies/')

    plt.clf()

    # plot control signal
    ax = plt.subplot(column[1])

    plt.grid()

    control_shift = 127
    plt.plot(
        [_2 - control_shift for _2 in (
            times_c
            + [_ + times_c[-1] for _ in times_c]
            + [_ + 2 * times_c[-1] for _ in times_c]
        )],
        control * 3
    )
    plt.ylim((60, 190))
    plt.xlim((0, time_length))
    #plt.xticks(time_ticks)
    #plt.xlim((0, LENGTH / 1e-6))
    plt.yticks((75, 125, 175))
    plt.xlabel(r'time in \SI{}{\micro\second}')


    plt.ylabel('current in mA')
    #plt.tight_layout()

    # plot frequencies
    ax = plt.subplot(column[0])
    ax.get_yaxis().set_label_coords(-.08,0.5)

    plt.grid()

    plt.ylabel('beat note in GHz')
    plt.text(37, 6.1, 'repumping', horizontalalignment='center')
    plt.text(37, .53, 'cooling', horizontalalignment='center')

    len_f = int(len(times_f) / 200 * time_length)
    shift = 0

    plt.plot((-1000, 10000), (6.835, 6.835), 'k--')
    plt.plot((-1000, 10000), (.25, .25), 'k--')

    plt.plot(times_f[:len_f], frequencies[shift:shift + len_f])
    plt.ylim((-0.2, 7.4))
    plt.xlim((0, time_length))
    plt.xticks(visible=False)


    plt.tight_layout()
    #plt.savefig(folder + get_fn(i))

    save_paper('real_jump_and_current')
    plt.show()



if __name__ == '__main__':
    folder = '/media/depot/data-2019/afmot/jump-generation/'
    plot_control_signal_and_frequencies(folder)
