from osci_to_frequency import do
from matplotlib import pyplot as plt

if __name__ == '__main__':
    folder = '/media/depot/data/afmot/decimation_curvdelay/'

    show_plot = False
    use_cache = False

    data = []

    delays = [1, 3, 5, 7, 10, 15, 25, 50, 100, 150, 200, 250, 400]
    decimations = (0, 1, 2, 3, 4, 5, 6, 7)
    #decimations = (6, 7)

    for decimation in decimations:
        d = []
        for delay in delays:
            filename = folder + 'decimation_%d_curvdelay_%dCH2.csv' % (decimation, delay)
            print(decimation, delay)
            try:
                d.append(
                    do(filename, True, False)
                )
            except:
                print('skipping', decimation, delay)
                continue

        data.append(d)

    for closeness in (0, 3, 6, 10):
        plt.clf()

        for i, data2 in enumerate(data):
            plt.plot(list(d['total_close_%d' % closeness] for d in data2), label='decimation %d' % decimations[i])

        plt.xticks(list(range(len(delays))))
        plt.gca().set_xticklabels([str(_) for _ in delays])

        plt.legend()
        plt.savefig(folder + 'total_close_%d.png' % closeness)
        plt.show()

    for target in (0, 1):
        for range_ in (0, 3, 6, 10):
            for i, data2 in enumerate(data):
                plt.plot(
                    list(d['target_%d_range_%d' % (target, range_)] for d in data2),
                    label='decimation %d' % decimations[i]
                )
            plt.xticks(list(range(len(delays))))
            plt.gca().set_xticklabels([str(_) for _ in delays])

            plt.legend()
            plt.savefig(folder + 'target_%d_range_%d.png' % (target, range_))
            plt.show()