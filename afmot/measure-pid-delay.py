import sys
sys.path += ['/home/ben/Schreibtisch']

from devices.cnt90 import CNT90
from matplotlib import pyplot as plt

c = CNT90()

#%%
import numpy as np

rate = 10000
length = 0.003
frequencies = c.frequency_measurement('B', length, rate, 'REAR')
times = list(_ * (1/rate) for _ in range(len(frequencies)))

plt.plot([_ / 1e-3 for _ in times], [_ / 1e6 for _ in frequencies])
plt.plot([0, 10], [25, 25])
plt.xlim((0, length / 1e-3))
plt.show()

