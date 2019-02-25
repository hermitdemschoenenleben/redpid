import pickle
import numpy as np
from matplotlib import pyplot as plt

import seaborn as sns
sns.set_context("talk")
sns.set()

LENGTH = 131.072e-6
filename = '/media/depot/data/2019/afmot-sequence-generation/control-signal.pickle'

with open(filename, 'rb') as f:
    d = pickle.load(f)

control = d['control_signals']

times = list(
    (t * LENGTH / 16384) / 1e-6
    for t in
    range(16384)
)
time_ticks = np.arange(0, 160, 20)

for i, d in enumerate(control):
    # convert to volt
    d = [c / 8192 for c in d]

    plt.plot(times, d, label=i)
    plt.ylim((-1.1, 1.1))
    plt.xticks(time_ticks)
    plt.xlim((0, LENGTH / 1e-6))
    plt.grid()

    plt.ylabel('control signal in V')
    plt.xlabel('time in microseconds')
    plt.tight_layout()

    plt.savefig(filename + '%d.png' % i)
    plt.clf()

#plt.legend()
#plt.show()