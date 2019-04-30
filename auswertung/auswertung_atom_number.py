import pickle
import numpy as np
from matplotlib import pyplot as plt
from gain_camera.utils import crop_imgs

FOLDER = '/media/depot/data/afmot/atom-numbers/'
FOLDER = '/home/ben/Schreibtisch/data/afmot_atom_numbers/'
#FOLDER = '/media/depot/data/fake-afmot/atom-numbers/'

input('not cropping!')

with open(FOLDER + 'test.pickle', 'rb') as f:
    all_data = pickle.load(f)

def sum_imgs(imgs):
    #imgs = imgs[2]
    #imgs = crop_imgs(imgs)
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

    for d in iterations:
        zero = d['N_background']

        N_afmot = d['N_afmot'] - zero
        N_mot = d['N_mot'] - zero

        zero = sum_imgs(d['img_background'])
        N_afmot = sum_imgs(d['img_afmot']) - zero
        N_mot = sum_imgs(d['img_mot']) - zero

        print('percentage', N_afmot / N_mot * 100)
        current_atom_numbers.append(N_afmot / N_mot * 100)
        mot_numbers.append(N_mot - zero)

        if duty_cycle > 0.6:
            #for img_idx in range(3):
            for img_idx in [0, 1, 2]:
                plt.subplot(1, 3, 1)
                plt.pcolormesh(d['img_background'][img_idx], vmax=100)
                plt.subplot(1, 3, 2)
                plt.pcolormesh(d['img_afmot'][img_idx], vmax=255)
                plt.subplot(1, 3, 3)
                plt.pcolormesh(crop_imgs(d['img_mot'])[img_idx], vmax=255)
                plt.show()

    relative_atom_numbers.append(
        np.mean(current_atom_numbers)
    )
    relative_atom_numbers_std.append(np.std(current_atom_numbers))

    print('result', relative_atom_numbers[-1], 'pm', relative_atom_numbers_std[-1])

print(relative_atom_numbers)

print('!!', np.std(mot_numbers[:10] / np.mean(mot_numbers[:10])))
print(len(mot_numbers))
#asd

plt.plot(duty_cycles, relative_atom_numbers)
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std)
plt.ylim([0, 110])
plt.xlim([0, 1])
plt.xlabel('cooling light duty cycle')
plt.ylabel('relative atom number')
#plt.savefig('afmot_relative_atom_number_too_good.svg')
plt.grid()
plt.xticks([0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1])
plt.yticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
plt.show()
