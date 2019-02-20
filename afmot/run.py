import numpy as np

from time import sleep
from matplotlib import pyplot as plt

from utils import counter_measurement, save_osci, N_BITS, LENGTH
from registers import Pitaya


if __name__ == '__main__':
    rp = Pitaya('rp-f012ba.local', user='root', password='zeilinger')
    rp.connect()

    rp.write_registers()

    datas = []

    delays = [1000, 5000, 10000]

    #for wait in (3.5, 4.5, 5.5, 6.5):
    for delay in delays:
        print('delay', delay)

        rp.set_algorithm(0)
        rp.set_enabled(0)

        rp.set_ff_target_directions([-1, 1, None, None])
        rp.set_ff_target_curvatures([1, 1, None, None])

        first_feed_forward = np.array([0] * LENGTH)
        rp.set_feed_forward(first_feed_forward, N_BITS)

        rp.sync()

        rp.start_clock(LENGTH, .5, 1, None)
        rp.enable_channel_b_loop_through(0)

        rp.set_curvature_filtering_starts([1000, 1000, None, None])
        #rp.set_max_state(4)

        rp.set_enabled(1)
        rp.pitaya.set('control_loop_sequence_player_keep_constant_at_end', 0)
        rp.set_algorithm(1)
        rp.pitaya.set('control_loop_sequence_player_record_after', delay)

        sleep(delay / 1000)
        d = rp._read_sequence(N_bits=14, N_points=16384)
        #d = rp.record_control_now()
        datas.append(d)
        plt.plot(d, label=str(delay))
        plt.show()

    plt.legend()
    plt.show()
