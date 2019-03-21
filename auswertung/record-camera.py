import dill
import rpyc
from matplotlib import pyplot as plt
import sys
import numpy as np
from time import sleep, time


if __name__ == '__main__':
    connection = rpyc.connect('gain.physik.hu-berlin.de', 8000)
    cams = connection.root.cams

    idx = 2
    cam = cams[idx]
    imgs = []
    times = []

    start_time = time()

    cam.set_exposure(-10)

    target_time = 10 # seconds

    i = 0
    while True:
        i += 1
        print(i)
        imgs.append(np.array(cam.snap_image()))
        times.append(time() - start_time)

        if times[-1] > target_time:
            break

    data = {
        'times': times,
        'imgs': imgs
    }

    with open('video.pickle', 'wb') as f:
        dill.dump(data, f)
