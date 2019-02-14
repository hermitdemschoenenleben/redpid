import pickle
from matplotlib import pyplot as plt

#with open('log-long.pickle', 'rb') as f:
with open('log-test2.pickle', 'rb') as f:
#with open('log-test.pickle', 'rb') as f:
#with open('log.pickle', 'rb') as f:
    data = pickle.load(f)

for d in data:
    N = d['N']
    print(N)
    ff = d['feed_forward']
    es = d['error_signal']
    frequencies = d['frequencies']

    #if N in (10, 20, 30, 40, 50, 60, 70):
    #if N in (500, 1000, 1500):#,50000):
    #if N in (1000, 2000, 3000, 4000, 12000):#, 5000, 6000, 6700, 8600):
    if N in (3000,3100, 3400):
    #if N in (80, 188):
    #if N in (6,7,8,9,10):
        #plt.plot(ff, label='feed forward')
        plt.plot([_ * 1000 for _ in es], label='error signal')
        plt.plot(frequencies, label='frequencies')

plt.legend()
#plt.ylim((-40, 40))
l = len(frequencies)
kwargs = {
    'color': 'k',
    'linestyle': '--'
}
#targets = (2500, 2400, -200, -600)
targets = (500, 400, -200, -600)
plt.axvline(x=int(l/4), **kwargs)
plt.plot([0, int(l/4)], [targets[0]] * 2, **kwargs)
plt.axvline(x=int(l/2), **kwargs)
plt.plot([int(l/4), int(l/2)], [targets[1]] * 2, **kwargs)
plt.axvline(x=int(3*l/4), **kwargs)
plt.plot([int(l/2), int(3*l/4)], [targets[2]] * 2, **kwargs)
plt.plot([int(3*l/4), l], [targets[3]] * 2, **kwargs)

plt.show()
