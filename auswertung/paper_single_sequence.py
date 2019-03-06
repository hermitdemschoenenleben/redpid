from osci_to_frequency import do
from matplotlib import pyplot as plt, gridspec
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
from plotting.utils import set_font_size, figsize

import seaborn as sns
#sns.set()
#sns.set_style('white')
#sns.set_context('talk')

FONT_SIZE = 14

set_font_size(FONT_SIZE)
row = gridspec.GridSpec(1, 2, width_ratios=[2, 1])

if __name__ == '__main__':
    folder = '/media/depot/data/afmot/decimation_curvdelay/'
    output_folder = '/home/ben/Schreibtisch/paper/plots/'

    decimation = 5
    delay = 15
    result = do(
        folder + 'decimation_%d_curvdelay_%dCH2.csv' % (decimation, delay),
        True, True
    )

    f = [_ / 1e8 for _ in result['combined']]
    dt = (result['times_fit'][1] - result['times_fit'][0]) / 1e-6

    parts = (
        (50, 700, 0.25),
        (770, 1350, 6.835)
    )

    for i, [start, stop, y] in enumerate(parts):
        f_part = f[start:stop]

        yticks = (y-0.01, y, y+0.01)
        ylim = (y-0.012, y+0.012)

        plt.clf()
        plt.gcf().set_size_inches(*figsize(1.65))
        
        plt.subplot(row[1])
        bin_max = y + 0.02
        bin_min = y - 0.02
        # 1 MHz size
        N_bins = 41
        plt.hist(
            f_part, N_bins, (bin_min, bin_max),
            orientation="horizontal", edgecolor='black',
            linewidth=1.2
        )
        plt.yticks([], visible=False)
        plt.ylim(ylim)

        plt.xlabel('#')
        plt.gca().set_aspect(7500)
        plt.tight_layout()
        #plt.savefig(output_folder + 'frequency-jump-histogram-%d.png' % i, transparent=True)
        #plt.show()
        #plt.clf()
        
          
        plt.subplot(row[0])

        # plot line width
        for height, shift, color in (
            (3/1000, -6/1000, 'r'),
            (6/1000, -3/1000, 'g'),
            (3/1000, 3/1000, 'r')
        ):
            rect = Rectangle((0, y + shift), 10000, height)
            # Create patch collection with specified colour/alpha
            pc = PatchCollection(
                [rect], facecolor=color, alpha=.2,
                edgecolor=color
            )
            # Add collection to axes
            plt.gca().add_collection(pc)


        plt.plot((0, 10000), (y, y), 'k--')
        plt.plot(
            [_ * dt for _ in list(range(len(f_part)))],
            f_part
        )
        plt.xlim((0, (stop-start)*dt))
        plt.yticks(yticks)
        plt.ylim(ylim)
        plt.ylabel('beat note in GHz')
        plt.xlabel('time in us')

        plt.tight_layout()
        plt.savefig(output_folder + 'frequency-jump-zoom-and-hist-%d.png' % i)
        #plt.show()
        plt.clf()

