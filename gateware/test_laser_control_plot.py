import pickle
from matplotlib import pyplot as plt

with open('log-continuous.pickle', 'rb') as f:
#with open('log.pickle', 'rb') as f:
    data = pickle.load(f)

for d in data:
    N = d['N']
    print(N)
    ff = d['feed_forward']
    es = d['error_signal']
    frequencies = d['frequencies']

    #if N in (10,80,180, 350, 500, 580):
    if N in (10, 20, 40):
        #plt.plot(ff, label='feed forward')
        #plt.plot(es, label='error signal')
        plt.plot(frequencies, label='frequencies')
        #plt.legend()

#plt.ylim((-40, 40))
plt.show()