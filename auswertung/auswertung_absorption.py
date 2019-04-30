#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from ben.plot_png import plt, save_paper, set_font_scale
#from matplotlib import pyplot as plt
import pickle
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage.filters import gaussian_filter
from scipy import constants
from matplotlib.ticker import MultipleLocator
#set_font_scale(2)

from matplotlib.pyplot import cm
COLORMAP = plt.cm.Spectral_r

hbar = constants.hbar
omega = 2 * np.pi * 384.23048e12
Gamma = 2 * np.pi * 6.066e6
Isat = 3.05e-3 * 1e4
Delta = (135.8-132.5)*1e6*8
s0 = hbar * omega * Gamma / (2 * Isat)
# I is a very rough estimate, but it doesn't matter as it is zero divided by Isat
I = 650e-6 / (np.pi * (30e-3)**2)
s = s0 / (1 + 4 * (Delta/Gamma) ** 2 + (I / Isat))

def asc_to_img(fn):
    with open(fn, 'r') as f:
        rows = f.readlines()

    return np.array([
        list(
                int(cell)
                for cell in
                row.split('\t')
        )
        for row in rows
    ])


def od_to_density(od, extent):
    px = 1.0 / 163.0 * 0.005
    column_density = od * px**2 / s
    density = column_density / extent
    cm = 0.01
    return density / cm**2

px_fluorescence = 1e-3 / 28.5


folder = '/run/media/ben/449D-DFAE/abs det test/'
#folder = '/home/ben/Schreibtisch/60s_355/'
folder = '/home/ben/Schreibtisch/abs-test-8/'
folder = '/home/ben/Schreibtisch/neuer-lock/'
folder = '/home/ben/Schreibtisch/lock-neu-24.2MHz/'

def rough_crop(img):
    return img
    return img[300:700, 300:700]

mot_densities = []
afmot_densities = []
relations = []

plot = False

def get_fn(idx):
    fn = 'data_%s.asc' % (
        ('000%d' % idx)[-4:]
    )
    return folder + fn

iteration = -1
while True:
    iteration += 1

    offset = 3 * iteration

    try:
        bg = rough_crop(asc_to_img(get_fn(1 + offset)))
        smot = rough_crop(asc_to_img(get_fn(2 + offset)))
        mot = rough_crop(asc_to_img(get_fn(3 + offset)))
    except FileNotFoundError:
        break



    if plot:
        vmax = 1024
        plt.subplot(1, 3, 1)
        plt.pcolormesh(bg, vmin=0, vmax=vmax)
        plt.subplot(1, 3, 2)
        plt.pcolormesh(smot, vmin=0, vmax=vmax)
        plt.subplot(1, 3, 3)
        plt.pcolormesh(mot, vmin=0, vmax=vmax)
        plt.colorbar()
        #plt.show()
        plt.clf()

    mot_size = 220 * px_fluorescence
    smot_size = 130 * px_fluorescence

    od_mot = (-np.log(mot / bg))
    od_smot = (-np.log(smot / bg))

    max_ = np.max([np.max(np.max(od_mot)), np.max(np.max(od_smot))])

    if plot:
        plt.subplot(1, 2, 1)
        plt.pcolormesh(od_mot, vmin=0, vmax=max_)
        plt.colorbar()
        plt.subplot(1, 2, 2)
        plt.pcolormesh(od_smot, vmin=0, vmax=max_)
        plt.colorbar()
        #plt.show()
        plt.clf()


    def get_maximum(img):
        filtered_img = gaussian_filter(img, 100)
        max_pos = np.argmax(filtered_img)
        cols = img.shape[1]
        col = max_pos % cols
        row = int(np.ceil(max_pos / cols))
        return row, col

    def get_crop(img, maximum, size):
        row, col = maximum
        print('max', row, col, 'shape', img.shape)
        half = int(size/2)

        plt.pcolormesh(img[row - half:row + half, col - half:col + half])
        plt.show()
        return img[row - half:row + half, col - half:col + half]

    maximum = get_maximum(od_mot)
    size = 500
    #filtered_od_mot = gaussian_filter(get_crop(od_mot, maximum, size), 5)
    #filtered_od_smot = gaussian_filter(get_crop(od_smot, maximum, size), 5)
    filtered_od_mot = gaussian_filter(od_mot, 5)
    filtered_od_smot = gaussian_filter(od_smot, 5)
    max_v = np.max(np.max(filtered_od_mot))
    print(max_v)

    if plot:
        plt.subplot(1, 2, 1)
        plt.pcolormesh(filtered_od_mot, vmin=0, vmax=max_v)
        plt.colorbar()
        plt.subplot(1, 2, 2)
        plt.pcolormesh(filtered_od_smot, vmin=0, vmax=max_v)
        plt.colorbar()
        #plt.show()
        plt.clf()

    normalize = False
    if normalize:
        norm = lambda img: img / max_v * 100
        filtered_od_mot = norm(filtered_od_mot)
        filtered_od_smot = norm(filtered_od_smot)
        max_v = 100

    mot_densities.append(np.max(np.max(filtered_od_mot)))
    afmot_densities.append(np.max(np.max(filtered_od_smot)))

    relation = afmot_densities[-1] / mot_densities[-1]
    relations.append(relation)
    print(relations)

    if plot:
        for i, [img, fn, size] in enumerate([(filtered_od_mot, 'mot', mot_size), (filtered_od_smot, 'smot', smot_size)]):
            fig = plt.gcf()
            #fig = plt.figure(i)
            plt.clf()
            #ax = fig.add_subplot(111, projection='3d')
            ax = Axes3D(fig)

            shape = img.shape

            x = np.linspace(0,  shape[1] / 163.0 * 0.005 / 1e-3, shape[1])
            y = np.linspace(0,  shape[0] / 163.0 * 0.005 / 1e-3, shape[0])

            X, Y = np.meshgrid(x, y)

            ax.plot_surface(X, Y, img, edgecolor='k', linewidth=.1, cmap=COLORMAP, vmax=max_v, vmin=0)
            ax.set_zlim((0, max_v))


            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False

            ax.xaxis.pane.set_edgecolor('white')
            ax.yaxis.pane.set_edgecolor('white')

            ax.grid(False)

            ax1 = ax
            # ticks towards the center
            ax1.xaxis._axinfo['tick']['inward_factor'] = 0
            ax1.xaxis._axinfo['tick']['outward_factor'] = 0.4
            ax1.yaxis._axinfo['tick']['inward_factor'] = 0
            ax1.yaxis._axinfo['tick']['outward_factor'] = 0.4
            ax1.zaxis._axinfo['tick']['inward_factor'] = 0
            ax1.zaxis._axinfo['tick']['outward_factor'] = 0.4
            ax1.zaxis._axinfo['tick']['outward_factor'] = 0.4
            ax.w_zaxis.line.set_lw(0.)
            ax.set_zticks([])
            ax.set_zticklabels([])

            ax.set_xticks([])
            ax.set_xticklabels([])

            ax.set_yticks([])
            ax.set_yticklabels([])

            plt.xlabel(r'$\leftarrow$\quad\quad 15mm\quad\quad $\rightarrow$')
            plt.ylabel(r'$\leftarrow$   15mm   $\rightarrow$')

            # move labels closer to image
            ax.xaxis.labelpad=-15
            ax.yaxis.labelpad=-15

            plt.savefig('%s.png' % fn, transparent=True)
            plt.show()
            #save_paper('%s_smot-density-%s' % (to_plot, fn), transparent=True)


        # plot color bar
        plt.gcf()
        #set_font_scale(3)
        m = cm.ScalarMappable(cmap=COLORMAP)

        m.set_array([0, max_v])
        cbar = plt.colorbar(m)
        cbar.set_label('optical density', labelpad=20)#, rotation=270)
        if normalize:
            ticks = [0, 20, 40, 60, 80, 100]
            cbar.set_ticks(ticks)
            cbar.set_ticklabels([
                '%d\%%' % percentage
                for percentage in ticks
            ])

        plt.tight_layout()
        ax = plt.gca()
        ax.remove()
        plt.tight_layout()
        #save_paper('density_colorbar', transparent=True)
    #plt.show()


print('mean', np.mean(relations), 'pm', np.std(relations))
print('mean MOT', np.mean(mot_densities), 'pm', np.std(mot_densities))
print('mean AFMOT', np.mean(afmot_densities), 'pm', np.std(afmot_densities))

plt.clf()
plt.plot(mot_densities)
plt.plot(afmot_densities)
plt.show()
plt.plot(relations)
plt.show()