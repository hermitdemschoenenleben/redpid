from time import time
import numpy as np
from gain_camera.utils import img2count, crop_imgs
from gain_camera.connection import Connection
from matplotlib import pyplot as plt
import pickle

def record_afmot_loading_old_style(pipe=None):
    c = Connection()
    c.connect()
    # important: using -12 or -12 leads to overexposed images for some reason...
    exposure = -11
    c.set_exposure_time(exposure)
    c.enable_trigger(True)
    c.run_continuous_acquisition()

    AFMOT = 0
    MOT = 1

    d = {}
    last_time = time()
    times = []
    atom_numbers = []

    def wait_for_frame():
        while True:
            c.parameters.call_listeners()

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

def record_afmot_loading_new_style(pipe=None):
    c = Connection()
    c.connect()
    # important: using -12 or -12 leads to overexposed images for some reason...
    # FIXME: Wrong exposure
    exposure = -11
    c.set_exposure_time(exposure)
    c.enable_trigger(True)
    c.run_continuous_acquisition()

    d = {}

    def wait_for_frame():
        while True:
            c.parameters.call_listeners()

            if c.image_data is not None:
                image_data = c.image_data
                c.image_data = None
                return time(), image_data

    assert c.image_data is None

    start_time = time()
    afmot_time, afmot = wait_for_frame()
    assert afmot_time - start_time > 10

    mot_time, mot = wait_for_frame()
    assert mot_time - afmot_time > 10

    d['img_afmot'] = afmot
    d['img_mot'] = mot

    new_time, imgs = wait_for_frame()


    for key, imgs in (('N_afmot', afmot), ('N_mot', mot)):
        atom_number = np.mean(
            [img2count(img, exposure) for img in imgs]
        )
        d[key] = atom_number

    #plt.plot([_['N_afmot'] for _ in data])
    #plt.plot([_['N_mot'] for _ in data])
    #plt.grid()
    #plt.show()
    if pipe is not None:
        pipe.send(pickle.dumps(d))

    return d

if __name__ == '__main__':
    record_afmot_loading()
