import json
import numpy as np
from ben.plot import plt

DURATION = 131.072e-6
LENGTH = 16384

import matplotlib
matplotlib.rcParams.update({'font.size': 18})


with open('control_history.json', 'r') as f:
    d = json.load(f)

raw = d['raw']
processed = d['data']

x_axis = np.linspace(0, DURATION * 1e6, LENGTH)

#for i in range(33):
for i in [0, 5, 15, 32]:
    #plt.plot(raw[-i-1][0], label='-%d raw' % i)
    #plt.plot(x_axis, raw[i][0], label='-%d raw' % i)
    plt.plot(x_axis, processed[i], label='step %d' % i)

    plt.xlabel('time [us]')
    plt.ylabel('control voltage [V]')
    plt.ylim((-1.1, 1.1))
    #plt.savefig('/home/ben/HU/Mini-Vortrag SMOT/control_%d.svg' % i)

plt.legend()
plt.show()