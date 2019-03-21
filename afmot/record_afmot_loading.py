from time import time
import numpy as np
from gain_camera.utils import img2count, crop_imgs
from gain_camera.gain_connection import Connection
from matplotlib import pyplot as plt
import pickle

cam_idxs = [1]

def record_afmot_loading(pipe=None):
    c = Connection()
    c.connect()
    try:
        c.enable_trigger(True, cam_idxs)
    except:
        pass

    exposure = -12
    c.set_exposure_time(exposure)

    AFMOT = 0
    MOT = 1

    for idx in cam_idxs:
        c.reset_frame_ready(idx)

    d = {}
    last_time = time()
    times = []
    atom_numbers = []

    for j in [AFMOT, MOT]:
        print('AMOT' if j == AFMOT else 'MOT')
        for img_number in range(10000000):
            print('record image number', img_number, end='\r')

            imgs = []

            for cam_idx in cam_idxs:
                c.wait_till_frame_ready(cam_idx)
                imgs.append(c.retrieve_image(cam_idx))

            new_time = time()
            times.append(new_time)

            for cam_idx in cam_idxs:
                # this is necessary for all cams in order to flush img cache
                c.reset_frame_ready(cam_idx)

            atom_number = np.mean([img2count(img, exposure) for img in imgs])
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
