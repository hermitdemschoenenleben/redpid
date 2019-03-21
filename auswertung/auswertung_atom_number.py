import pickle
import numpy as np
from matplotlib import pyplot as plt

FOLDER = '/media/depot/data/afmot/atom-numbers/'

with open(FOLDER + 'test.pickle', 'rb') as f:
    all_data = pickle.load(f)

relative_atom_numbers = []

for iterations in all_data:
    current_atom_numbers = []

    for d in iterations:
        zero = np.mean(d['atom_numbers'][:5])

        N_afmot = d['N_afmot'] - zero
        #N_mot = d['N_mot'] - zero
        N_mot = np.mean(d['atom_numbers'][-5:]) - zero

        print('percentage', N_afmot / N_mot * 100)
        current_atom_numbers.append(N_afmot / N_mot * 100)

        plt.plot(d['times'], [_ - zero for _ in d['atom_numbers']])
        plt.show()

        plt.pcolormesh(d['img_mot'][0])
        plt.show()

    relative_atom_numbers.append(
        np.mean(current_atom_numbers)
    )

print(relative_atom_numbers)

plt.plot(relative_atom_numbers)
plt.show()