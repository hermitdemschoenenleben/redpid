import dill
from matplotlib import pyplot as plt

with open('video.pickle', 'rb') as f:
    d = dill.load(f)

imgs = d['imgs']
times = d['times']

print('duration', times[-1] - times[0])

for img in imgs[::10]:
    plt.pcolormesh(img, vmin=0, vmax=255)
    plt.show()