import klepto
import pickle
import numpy as np
from seaborn import color_palette
from matplotlib import pyplot as plt
from gain_camera.utils import crop_imgs

FOLDER = '/media/depot/data/afmot/atom-numbers/'

def load_atom_numbers_new(filename):
    input('ist crop richtig?')
    def sum_imgs(imgs):
        #imgs = crop_imgs(imgs)
        """plt.pcolormesh(imgs[0])
        plt.show()
        plt.pcolormesh(imgs[1])
        plt.show()
        plt.pcolormesh(imgs[2])
        plt.show()"""
        img_sums = [np.sum(np.sum(img)) for img in imgs]
        return np.sum(img_sums)

    archive = klepto.archives.dir_archive(FOLDER + filename, serialized=True)
    archive.sync()

    def _get_key(cooling_duty_cycle, it):
        return '%.4f-%d' % (cooling_duty_cycle, it)

    def _get(cooling_duty_cycle, it):
        return archive[_get_key(cooling_duty_cycle, it)]

    relative_atom_numbers = []
    relative_atom_numbers_std = []
    duty_cycles = []

    mot_numbers = []

    for duty_cycle in archive['duty_cycles']:
        print(duty_cycle)
        duty_cycles.append(duty_cycle)

        current_atom_numbers = []

        iteration = 0
        while True:
            print(iteration)

            try:
                d = _get(duty_cycle, iteration)
            except KeyError:
                break

            zero = d['N_background']

            N_afmot = d['N_afmot'] - zero
            N_mot = d['N_mot'] - zero

            zero = sum_imgs(d['img_background'])
            N_afmot = sum_imgs(d['img_afmot']) - zero
            N_mot = sum_imgs(d['img_mot']) - zero

            #plt.pcolormesh(d['img_afmot'][0])
            #plt.show()

            print('percentage', N_afmot / N_mot * 100)
            current_atom_numbers.append(N_afmot / N_mot * 100)
            mot_numbers.append(N_mot - zero)

            iteration += 1

        relative_atom_numbers.append(
            np.mean(current_atom_numbers)
        )
        relative_atom_numbers_std.append(np.std(current_atom_numbers))

        print('result', relative_atom_numbers[-1], 'pm', relative_atom_numbers_std[-1])

    relative_atom_numbers = np.array(relative_atom_numbers) - relative_atom_numbers[0]
    return duty_cycles, relative_atom_numbers, relative_atom_numbers_std


def load_atom_numbers_old(filename):
    with open(FOLDER + filename, 'rb') as f:
        all_data = pickle.load(f)

    def sum_imgs(imgs):
        #imgs = imgs[2]
        imgs = crop_imgs(imgs)
        #for img in imgs:
        #    plt.pcolormesh(img)
        #    plt.show()
        img_sums = [np.sum(np.sum(img)) for img in imgs]
        return np.sum(img_sums)


    relative_atom_numbers = []
    relative_atom_numbers_std = []
    duty_cycles = []

    mot_numbers = []

    for duty_cycle, iterations in all_data.items():
        print('DUTY', duty_cycle)
        duty_cycles.append(duty_cycle)

        current_atom_numbers = []

        for d in iterations[:10]:
            zero = d['N_background']

            N_afmot = d['N_afmot'] - zero
            N_mot = d['N_mot'] - zero

            zero = sum_imgs(d['img_background'])
            N_afmot = sum_imgs(d['img_afmot']) - zero

            N_mot = sum_imgs(d['img_mot']) - zero

            print('percentage', N_afmot / N_mot * 100)
            current_atom_numbers.append(N_afmot / N_mot * 100)
            mot_numbers.append(N_mot - zero)

            """if duty_cycle > 0.6:
                #for img_idx in range(3):
                for img_idx in [0, 1, 2]:
                    plt.subplot(1, 3, 1)
                    plt.pcolormesh(d['img_background'][img_idx], vmax=100)
                    plt.subplot(1, 3, 2)
                    plt.pcolormesh(d['img_afmot'][img_idx], vmax=255)
                    plt.subplot(1, 3, 3)
                    plt.pcolormesh(crop_imgs(d['img_mot'])[img_idx], vmax=255)
                    plt.show()"""

        relative_atom_numbers.append(
            np.mean(current_atom_numbers)
        )
        relative_atom_numbers_std.append(np.std(current_atom_numbers))

        print('result', relative_atom_numbers[-1], 'pm', relative_atom_numbers_std[-1])

    print(relative_atom_numbers)

    print('!!', np.std(mot_numbers[:10] / np.mean(mot_numbers[:10])))
    print(len(mot_numbers))
    #asd

    relative_atom_numbers = np.array(relative_atom_numbers) - relative_atom_numbers[0]

    return duty_cycles, relative_atom_numbers, relative_atom_numbers_std