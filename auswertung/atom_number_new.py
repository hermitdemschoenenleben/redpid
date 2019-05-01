import klepto
import numpy as np
from seaborn import color_palette
from matplotlib import pyplot as plt
from gain_camera.utils import crop_imgs

def sum_imgs(imgs):
    #imgs = imgs[2]
    imgs = crop_imgs(imgs)
    #for img in imgs:
    #    plt.pcolormesh(img)
    #    plt.show()
    img_sums = [np.sum(np.sum(img)) for img in imgs]
    return np.sum(img_sums)

palette = color_palette()
palette = [palette[1], palette[0], *palette[2:]]

markers = ('o', 'v', '^', 's', '*')

FOLDER = '/home/ben/Schreibtisch/data/afmot_atom_numbers/'
FILENAME = '1.9kHz'

archive = klepto.archives.dir_archive(FOLDER + FILENAME, serialized=True)
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

        if iteration != 5:
            iteration += 1
            continue

        zero = d['N_background']

        N_afmot = d['N_afmot'] - zero
        N_mot = d['N_mot'] - zero

        zero = sum_imgs(d['img_background'])
        N_afmot = sum_imgs(d['img_afmot']) - zero
        N_mot = sum_imgs(d['img_mot']) - zero

        print('percentage', N_afmot / N_mot * 100)
        current_atom_numbers.append(N_afmot / N_mot * 100)
        mot_numbers.append(N_mot - zero)

        if duty_cycle == .9:
            plt.pcolormesh(d['img_mot'][2])
            plt.show()
            plt.pcolormesh(d['img_afmot'][2])
            plt.show()

        iteration += 1
    
    relative_atom_numbers.append(
        np.mean(current_atom_numbers)
    )
    relative_atom_numbers_std.append(np.std(current_atom_numbers))

    print('result', relative_atom_numbers[-1], 'pm', relative_atom_numbers_std[-1])

plt.plot(duty_cycles, relative_atom_numbers, color=palette[1], marker=markers[1])
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std, color=palette[1])
plt.show()