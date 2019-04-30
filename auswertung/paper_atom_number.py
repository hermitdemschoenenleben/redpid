import dill
import pickle
import numpy as np
from matplotlib import pyplot as plt
from gain_camera.utils import crop_imgs
from ben.plot import plt, save_ma, save_paper, set_font_size
from seaborn import color_palette

palette = color_palette()
palette = [palette[1], palette[0], *palette[2:]]
markers = ('o', 'v', '^', 's', '*')
set_font_size(15)

FOLDER = '/media/depot/data/afmot/atom-numbers/'
#FOLDER = '/media/depot/data/fake-afmot/atom-numbers/'

plt.clf()

#input('not cropping!')

with open(FOLDER + '19-04-10-gut.pickle', 'rb') as f:
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

duty_cycles = [_ * 100 for _ in duty_cycles]
plt.plot(duty_cycles, relative_atom_numbers, color=palette[1], marker=markers[1], label='7.6 kHz')
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std, color=palette[1])






# PLOT REFERENCE DATA

fake_folder = '/media/depot/fake_smot/'
fake_dataset = (
    '7.5 kHz',
    'both_7.5kHz_d0',
    list(np.linspace(0, 1, 41)),
    1
)
name, fn, percentages, repetitions = fake_dataset
species = 87
with open(fake_folder + str(species) + '_' + fn + '.pickle', 'rb') as f:
    data = dill.load(f)

idx = lambda perc_idx, rep: rep * len(percentages) + perc_idx

assert percentages[0] == 0
offset = data[0]['N_smot']

smot_numbers = [_['N_smot'] for _ in data]
smot_numbers_std = [
    (
        np.std(list(
            [_['N_smot'] for _ in data][idx(perc_idx, rep)]
            for rep in range(repetitions)
        ))
    )
    for perc_idx, perc in enumerate(percentages)
]
smot_numbers = [
    (
        np.mean(list(
            smot_numbers[idx(perc_idx, rep)] - offset
            #- initial_offsets[idx(perc_idx, rep)]
            for rep in range(repetitions)
        ))
    )
    for perc_idx, perc in enumerate(percentages)
]

#mot_numbers = [_['N_mot'] for _ in data]
mot_numbers = [np.mean(_['atom_numbers'][-20:]) for _ in data]
mot_numbers = [
    (
        np.mean(list(
            mot_numbers[idx(perc_idx, rep)] - offset
            #- initial_offsets[idx(perc_idx, rep)]
            for rep in range(repetitions)
        ))
    )
    for perc_idx, perc in enumerate(percentages)
]

results = np.array([sm / m *100 for sm, m in zip(smot_numbers, mot_numbers)])
results[results<0] = 0

"""plt.plot(
    [_ * 100 for _ in percentages],
    results,
    label='AOM-switched dual-laser MOT',
    linewidth=2
)"""


plt.ylim([0, 100])
plt.xlim([0, 100])

plt.xlabel(r'duty cycle $C$ in $\%$')
plt.ylabel(r'relative atom number in $\%$')

plt.grid()
plt.xticks([0, 20, 40, 60, 80, 100])
plt.yticks([0, 20, 40, 60, 80, 100])
plt.tight_layout()
plt.legend(loc='upper left')

save_paper('real_afmot', svg=True)
plt.show()