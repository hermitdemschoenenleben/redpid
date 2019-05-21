import klepto
import numpy as np
from seaborn import color_palette
from matplotlib import pyplot as plt
from gain_camera.utils import crop_imgs
from load_atom_numbers import load_atom_numbers_new, load_atom_numbers_old

palette = color_palette()
palette = [palette[1], palette[0], *palette[2:]]

markers = ('o', 'v', '^', 's', '*')

FILENAME = '1.9kHz'
duty_cycles, relative_atom_numbers, relative_atom_numbers_std = load_atom_numbers_new(FILENAME)
plt.plot(duty_cycles, relative_atom_numbers, color=palette[1], marker=markers[1])
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std, color=palette[1])

duty_cycles, relative_atom_numbers, relative_atom_numbers_std = load_atom_numbers_old('19-04-10-gut.pickle')
plt.plot(duty_cycles, relative_atom_numbers, color=palette[1], marker=markers[1])
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std, color=palette[1])


plt.show()