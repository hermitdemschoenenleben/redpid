import pickle
from matplotlib import pyplot as plt

with open('log.pickle', 'rb') as f:
    data = pickle.load(f)

for d in data:
    N = d['N']
    print(N)
    ff = d['feed_forward']
    es = d['error_signal']
    frequencies = d['frequencies']

    if N in (70,100,140,170, 230, 260):
        #plt.plot(ff, label='feed forward')
        #plt.plot(es, label='error signal')
        plt.plot(frequencies, label='frequencies')
        #plt.legend()

#plt.ylim((-40, 40))
plt.show()