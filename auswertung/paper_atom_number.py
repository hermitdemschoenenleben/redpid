import dill
import pickle
import numpy as np
from matplotlib import pyplot as plt
from gain_camera.utils import crop_imgs
from ben.plot import plt, save_ma, save_paper, set_font_size
from seaborn import color_palette
from load_atom_numbers import load_atom_numbers_new, load_atom_numbers_old

palette = color_palette()
palette = [palette[1], palette[0], *palette[2:]]
markers = ('o', 'v', '^', 's', '*')
set_font_size(16)

plt.clf()


duty_cycles, relative_atom_numbers, relative_atom_numbers_std = load_atom_numbers_old('19-04-10-gut.pickle')
duty_cycles = [_ * 100 for _ in duty_cycles]
plt.plot(duty_cycles, relative_atom_numbers, color=palette[1], marker=markers[1], label='7.6 kHz')
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std, color=palette[1])

FILENAME = '1.9kHz'
duty_cycles, relative_atom_numbers, relative_atom_numbers_std = load_atom_numbers_new(FILENAME)
duty_cycles = [_ * 100 for _ in duty_cycles]
duty_cycles = list(duty_cycles) + [100]
relative_atom_numbers = list(relative_atom_numbers) + [relative_atom_numbers[0]]
relative_atom_numbers_std = list(relative_atom_numbers_std) + [relative_atom_numbers_std[0]]

plt.plot(duty_cycles, relative_atom_numbers, color=palette[2], marker=markers[2], label='1.9 kHz')
plt.errorbar(duty_cycles, relative_atom_numbers, yerr=relative_atom_numbers_std, color=palette[2])


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