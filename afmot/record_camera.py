import os
import dill
import numpy as np

os.chdir('C:\\Users\\gain\\Documents\\The Imaging Source Europe GmbH\\TIS Grabber DLL\\bin\\win32')
import icpy3

from time import time
from matplotlib import pyplot as plt


class Camera:
    def __init__(self, idx):
        filename = 'camera%d' % idx
        try:
            cam = ic.get_device_by_file(filename)
            cam.exposure.value
        except:
            print('opening camera %d' % idx)
            cam = ic.get_device_by_dialog()
            cam.save_device_state(filename)

        cam.exposure.value = -13
        cam.prepare_live()
        self.cam = cam
        self.background = None

    def snap_image(self):
        self.cam.start_live()
        self.cam.snap_image()
        data = self.retrieve_image()
        self.cam.suspend_live()

        return data

    def retrieve_image(self):
        [d, img_height, img_width, img_depth] = self.cam.get_image_data()
        img_depth = int(img_depth)
        img = np.ndarray(buffer = d, dtype = np.uint8, shape = (img_width, img_height, img_depth))
        data = img[:,:,0].astype(np.int16)

        return data

    def save_image(self, filename):
        self.cam.save_image(filename, 0)

    def enable_trigger(self, enable):
        if enable:
            #self.cam.enable_continuous_mode(True)
            self.cam.start_live()
            self.cam.register_frame_ready_callback()
            self.enable_trigger(True)
        else:
            self.cam.enable_trigger(False)

    def calibrate(self):
        for i in range(10):
            self.snap_image()

        self.background = img2count(self.snap_image(), self, subtract_background=False)


def img2count(img, cam, subtract_background=True):
    count = np.sum(
        np.sum(img)) / 1e9 / (10 * (2 ** (cam.cam.exposure.value))
    )

    if subtract_background:
        assert cam.background is not None, 'camera not calibrated'
        count -= cam.background

    return count


def crop_imgs(imgs):
    bounds = (
        ((0, 350), (175, 525)),
        ((55, 405), (200, 550)),
        ((0, 350), (140, 490))
    )
    new_imgs = []

    for i, img in enumerate(imgs):
        b = bounds[i]
        new_imgs.append(img[b[0][0]:b[0][1],b[1][0]:b[1][1]])

    return new_imgs


if __name__ == '__main__':
    ic = icpy3.IC_ImagingControl()
    ic.init_library()

    cams = [Camera(idx) for idx in range(3)]

    for cam in cams:
        try:
            cam.cam.suspend_live()
        except:
            pass

    #cam.set_format(0)
    #cam.snap_image()

    input('ready for calibration?')
    for cam in cams:
        cam.calibrate()

    for cam in cams:
        cam.cam.enable_continuous_mode(True)

    for i in range(3):
        # for some strange reason this does not work when inside Camera class
        cams[i].cam.start_live()
        if not cams[i].cam.callback_registered:
            cams[i].cam.register_frame_ready_callback()
        cams[i].cam.enable_trigger(True)
    #%%


    """
    input('background')
    backgrounds = [cam.snap_image() for cam in cams]
    input('continue')
    """

    for task in range(13):
        print('TASK!!!!', task)
        SMOT = 0
        MOT = 1

        data = []
        
        for iteration in range(41):
            print('iteration', iteration)
            for cam in cams:
                cam.cam.reset_frame_ready()
        
            d = {}
            last_time = time()
            times = []
            atom_numbers = []
        
            for j in [SMOT, MOT]:
                print('SMOT' if j == SMOT else 'MOT')
                for img_number in range(10000000):
                    #cams[0].cam.wait_til_frame_ready()
        
                    imgs = []
        
                    for cam in cams:
                        cam.cam.wait_til_frame_ready()
                        imgs.append(cam.retrieve_image())
        
                    new_time = time()
                    times.append(new_time)
        
                    for cam in cams:
                        # this is necessary for all cams in order to flush img cache
                        cam.cam.reset_frame_ready()
        
                    atom_number = np.mean([img2count(img, cam) for img, cam in zip(imgs, cams)])
                    atom_numbers.append(atom_number)
        
                    if new_time - last_time > 1 and img_number > 0:
                        #for img in imgs:
                        #    plt.pcolormesh(img)
                        #    plt.show()
                        if j == SMOT:
                            d['N_smot'] = atom_number
                            d['img_smot_live'] = crop_imgs(last_imgs)
                            d['img_smot_after'] = crop_imgs(imgs)
                        else:
                            d['N_mot'] = atom_number
                            d['img_mot'] = crop_imgs(imgs)
        
                        break
        
                    last_time = new_time
                    last_imgs = imgs
        
            times = [_ - times[0] for _ in times]
            plt.plot(times, atom_numbers)
            plt.grid()
            plt.show()
        
            d.update({
                'times': times,
                'atom_numbers': atom_numbers,
            })
        
            data.append(d)
        
            plt.plot([_['N_smot'] for _ in data])
            plt.plot([_['N_mot'] for _ in data])
            plt.grid()
            plt.show()

       
        with open('task_%d.pickle' % task, 'wb') as f:
            dill.dump(data, f)
