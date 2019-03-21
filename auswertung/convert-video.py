import os
import numpy as np
import dill
import subprocess
from matplotlib import pyplot as plt

filename = '/media/depot/data/video0.pickle'
target_time = 6

with open(filename, 'rb') as f:
    d = dill.load(f)

imgs = d['imgs']
times = d['times']

print('duration', times[-1] - times[0])


os.chdir('/tmp')

FPS = len(times) / times[-1]
"""
for i, [img, time] in enumerate(zip(imgs, times)):
    if time >= target_time:
        break

    if i < 2:
        img = np.array([[0] * 125] * 125)
    else:
        img = (np.array(img[225:350, 325:450]) * -1) + 255

    plt.pcolormesh(img, vmin=100, vmax=235, cmap='binary')
    plt.xticks([])
    plt.yticks([])
    plt.gca().set_aspect(1)
    plt.tight_layout()
    plt.savefig('img%s.png' % (('0000000%d' % i)[-5:]), bbox_inches='tight')
"""
subprocess.Popen(
    'ffmpeg -y -framerate %f -i /tmp/img%%05d.png -c:v libx264 -profile:v high '
    '-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" '
    '-crf 20 -pix_fmt yuv420p %s.mp4' % (FPS, filename),
    shell=True
)