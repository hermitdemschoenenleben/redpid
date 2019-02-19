import json
import numpy as np

from time import sleep
from matplotlib import pyplot as plt

from utils import do, copy_file, counter_measurement, save_osci, \
    REPLAY_SHIFT, N_BITS, LENGTH
from registers import Pitaya
from process_control import process_control_data


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()

    rp.write_registers()

    datas = []

    for wait in (3.5, 4.5, 5.5, 6.5):
        print('wait', wait)

        rp.pitaya.set('control_loop_sequence_player_run_algorithm', 0)
        rp.pitaya.set('control_loop_sequence_player_enabled', 0)

        rp.pitaya.set('control_loop_sequence_player_ff_direction_0', -1)
        rp.pitaya.set('control_loop_sequence_player_ff_direction_1', 1)
        rp.pitaya.set('control_loop_sequence_player_ff_curvature_0', 1)
        rp.pitaya.set('control_loop_sequence_player_ff_curvature_1', 1)

        first_feed_forward = np.array([0] * LENGTH)
        #rp.set_feed_forward(first_feed_forward, N_BITS)

        rp.sync()

        rp.start_clock(LENGTH, .5, 1, None)
        rp.pitaya.set('control_loop_dy_sel', rp.pitaya.signal('zero'))
        #rp.pitaya.set('control_loop_dy_sel', rp.pitaya.signal('control_loop_other_x'))

        rp.pitaya.set('control_loop_sequence_player_mean_start', 100)
        rp.pitaya.set('control_loop_sequence_player_max_state', 4)

        rp.pitaya.set('control_loop_sequence_player_enabled', 1)
        rp.pitaya.set('control_loop_sequence_player_keep_constant_at_end', 0)
        rp.pitaya.set('control_loop_sequence_player_run_algorithm', 1)

        rp.pitaya.set('root_sync_sequences_en', 1)
        rp.pitaya.set('root_sync_sequences_en', 0)

        asd
        sleep(wait)
        d = rp.record_control()
        datas.append(d)
        plt.plot(d, label=wait)
        plt.show()

        asd

    plt.legend()
    plt.show()
