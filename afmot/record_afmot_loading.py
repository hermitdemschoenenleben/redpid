from time import time
import numpy as np
from gain_camera.utils import img2count, crop_imgs
from gain_camera.gain_connection import Connection
from matplotlib import pyplot as plt
import pickle

def record_afmot_loading(pipe=None):
    c = Connection()
    c.connect()
    c.enable_trigger(True)
    c.run_continuous_acquisition()
    exposure = -12
    c.set_exposure_time(exposure)

    AFMOT = 0
    MOT = 1

    d = {}
    last_time = time()
    times = []
    atom_numbers = []

    def wait_for_frame():
        while True:
            c.call_listeners()

            if c.image_data is not None:
                image_data = c.image_data
                c.image_data = None
                return time(), image_data

    for j in [AFMOT, MOT]:
        print('AMOT' if j == AFMOT else 'MOT')
        for img_number in range(10000000):
            print('record image number', img_number, end='\r')

            new_time, imgs = wait_for_frame()
            times.append(new_time)

            atom_number = np.mean(
                [img2count(img, exposure) for img in imgs]
            )
            atom_numbers.append(atom_number)

            if new_time - last_time > 1 and img_number > 0:
                #for img in imgs:
                #    plt.pcolormesh(img)
                #    plt.show()
                if j == AFMOT:
                    d['N_afmot'] = atom_number
                    d['img_afmot_live'] = crop_imgs(last_imgs)
                    d['img_afmot_after'] = crop_imgs(imgs)
                else:
                    d['N_mot'] = atom_number
                    d['img_mot'] = crop_imgs(imgs)

                break

            last_time = new_time
            last_imgs = imgs

    times = [_ - times[0] for _ in times]

    #plt.plot(times, atom_numbers)
    #plt.grid()
    #plt.show()

    d.update({
        'times': times,
        'atom_numbers': atom_numbers,
    })

    #data.append(d)

    #plt.plot([_['N_afmot'] for _ in data])
    #plt.plot([_['N_mot'] for _ in data])
    #plt.grid()
    #plt.show()
    if pipe is not None:
        pipe.send(pickle.dumps(d))

    return d


if __name__ == '__main__':
    record_afmot_loading()
