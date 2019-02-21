import pickle
from matplotlib import pyplot as plt

with open('run.pickle', 'rb') as f:
    d = pickle.load(f)

control = d['control_signals']

for i, d in enumerate(control[-5:]):
    plt.plot(d, label=i)

plt.legend()
plt.show()