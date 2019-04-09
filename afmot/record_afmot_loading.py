import pickle
import numpy as np

from time import time, sleep
from gain_camera.utils import img2count, crop_imgs
from gain_camera.connection import Connection
from matplotlib import pyplot as plt
from multiprocessing import Process, Pipe


def start_acquisition_process(old_style=False):
    pipe, child_pipe = Pipe()

    if old_style:
        acquiry_process = Process(target=record_afmot_loading_old_style, args=(child_pipe,))
    else:
        acquiry_process = Process(target=record_afmot_loading_new_style, args=(child_pipe,))

    acquiry_process.start()

    # wait until acquiry process is ready
    pipe.recv()
    print('child is ready!')

    return acquiry_process, pipe


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
    exposure = -8
    c.set_exposure_time(exposure)
    c.enable_trigger(True)
    c.run_continuous_acquisition()

    d = {}

    def wait_for_frame():
        while True:
            c.parameters.call_listeners(no_timer=True)

            if c.image_data is not None:
                image_data = c.image_data
                c.image_data = None
                return time(), image_data

    c.parameters.call_listeners(no_timer=True)
    sleep(1)
    c.parameters.call_listeners(no_timer=True)
    # reset image data
    c.image_data = None

    # tell the main thread that we're ready
    pipe.send(True)

    start_time = time()

    background_time, background = wait_for_frame()
    print('bg image at', background_time - start_time)

    afmot_time, afmot = wait_for_frame()
    print('recorded afmot image at', afmot_time - start_time)
    assert afmot_time - start_time > 10

    mot_time, mot = wait_for_frame()
    print('recorded mot image at', mot_time - start_time)
    assert mot_time - afmot_time > 10

    d['img_background'] = background
    d['img_afmot'] = afmot
    d['img_mot'] = mot

    for key, imgs in (('N_background', background), ('N_afmot', afmot), ('N_mot', mot)):
        atom_number = np.mean(
            [img2count(img, exposure) for img in imgs]
        )
        d[key] = atom_number

    """plt.pcolormesh(d['img_background'][0])
    plt.show()
    plt.pcolormesh(d['img_afmot'][0])
    plt.show()
    plt.pcolormesh(d['img_mot'][0])
    plt.show()"""
    #plt.plot([_['N_afmot'] for _ in data])
    #plt.plot([_['N_mot'] for _ in data])
    #plt.grid()
    #plt.show()

    print('ratio', (d['N_afmot'] - d['N_background']) / (d['N_mot'] - d['N_background']))

    if pipe is not None:
        pipe.send(pickle.dumps(d))

    return d

if __name__ == '__main__':
    record_afmot_loading()
